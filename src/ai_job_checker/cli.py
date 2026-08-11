from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone

from . import databricks_cli
from .state import config_path, load_json, local_dir, save_json, state_path


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    remedy: str = ""


def _command_version(command: str, *args: str) -> str | None:
    if shutil.which(command) is None:
        return None
    result = subprocess.run([command, *args], text=True, capture_output=True, check=False)
    return (result.stdout or result.stderr).strip().splitlines()[0]


def doctor(_: argparse.Namespace) -> int:
    checks: list[Check] = []
    python_ok = sys.version_info >= (3, 10)
    checks.append(Check("Python", python_ok, platform.python_version(), "Python 3.10 이상을 설치하세요."))

    node_output = _command_version("node", "--version")
    node_version = databricks_cli.parse_version(node_output or "")
    checks.append(Check("Node.js", bool(node_version and node_version >= (18, 0, 0)), node_output or "설치되지 않음", "Node.js 18 이상을 설치하세요."))

    cli_output = _command_version("databricks", "--version")
    cli_version = databricks_cli.parse_version(cli_output or "")
    checks.append(Check("Databricks CLI", bool(cli_version and cli_version >= databricks_cli.MINIMUM_VERSION), cli_output or "설치되지 않음", "https://docs.databricks.com/dev-tools/cli/install 에서 최신 CLI를 설치하세요."))

    if cli_version and cli_version >= databricks_cli.MINIMUM_VERSION:
        try:
            profiles = databricks_cli.list_profiles()
            valid = sum(profile.valid for profile in profiles)
            checks.append(Check("Databricks 인증", valid > 0, f"profile {len(profiles)}개 중 유효 {valid}개", "databricks auth login --host <workspace-url> --profile <name> 을 실행하세요."))
        except RuntimeError as error:
            checks.append(Check("Databricks 인증", False, str(error), "databricks auth profiles를 확인하세요."))

    for check in checks:
        marker = "PASS" if check.ok else "FAIL"
        print(f"[{marker}] {check.name}: {check.detail}")
        if not check.ok and check.remedy:
            print(f"       해결: {check.remedy}")
    print("\n다음 명령: ./setup.sh configure" if all(check.ok for check in checks) else "\n실패 항목을 해결한 후 ./setup.sh doctor를 다시 실행하세요.")
    return 0 if all(check.ok for check in checks) else 1


def _choose_profile(requested: str | None) -> databricks_cli.Profile:
    profiles = databricks_cli.list_profiles()
    if not profiles:
        raise RuntimeError("등록된 Databricks profile이 없습니다.")
    print("사용 가능한 Databricks profiles:")
    for profile in profiles:
        validity = "인증됨" if profile.valid else "인증 필요"
        print(f"  - {profile.name}: {profile.host} ({validity})")

    chosen = requested
    if chosen is None:
        if not sys.stdin.isatty():
            raise RuntimeError("profile을 자동 선택하지 않습니다. --profile <name>을 지정하세요.")
        chosen = input("사용할 profile 이름: ").strip()

    matches = [profile for profile in profiles if profile.name == chosen]
    if not matches:
        raise RuntimeError(f"알 수 없는 profile: {chosen}")
    if not matches[0].valid:
        raise RuntimeError(f"profile '{chosen}'의 인증을 먼저 완료하세요.")
    return matches[0]


def configure(args: argparse.Namespace) -> int:
    profile = _choose_profile(args.profile)
    current_user = databricks_cli.run("current-user", "me", profile=profile.name)
    if current_user.returncode != 0:
        raise RuntimeError(current_user.stderr.strip() or "현재 사용자를 확인할 수 없습니다.")

    existing = load_json(config_path())
    values = {
        "profile": profile.name,
        "workspace_host": profile.host,
        "warehouse_id": args.warehouse_id or existing.get("warehouse_id"),
        "catalog": args.catalog or existing.get("catalog", "ai_job_checker"),
        "schema": args.schema or existing.get("schema", "ops"),
        "model": args.model or existing.get("model", "databricks-claude-sonnet-4-6"),
        "default_report_locale": args.report_locale or existing.get("default_report_locale", "ko"),
    }
    if not values["warehouse_id"]:
        raise RuntimeError("warehouse를 자동 선택하지 않습니다. --warehouse-id <id>를 지정하세요.")
    save_json(config_path(), values)
    save_json(state_path(), {"stage": "configured", "updated_at": datetime.now(timezone.utc).isoformat()})
    print(f"설정을 저장했습니다: {config_path()}")
    print("secret/token은 저장하지 않았습니다.")
    print("\n다음 명령: ./setup.sh status")
    return 0


def status(_: argparse.Namespace) -> int:
    config = load_json(config_path())
    setup_state = load_json(state_path())
    if not config:
        print("상태: 설정 전")
        print(f"설정 예시: {local_dir() / 'config.example.json'}")
        print("다음 명령: ./setup.sh configure")
        return 0
    print(f"상태: {setup_state.get('stage', 'configured')}")
    print(json.dumps(config, ensure_ascii=False, indent=2, sort_keys=True))
    print("다음 명령: ./setup.sh admin-pack")
    return 0


def _configured() -> dict[str, object]:
    config = load_json(config_path())
    if not config:
        raise RuntimeError("먼저 ./setup.sh configure를 실행하세요.")
    return config


def _run_checked(command: list[str]) -> None:
    print(f"실행: {' '.join(command)}")
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"명령이 실패했습니다(exit {result.returncode}): {' '.join(command)}")


def _bundle_vars(config: dict[str, object]) -> list[str]:
    return [
        "--var", f"warehouse_id={config['warehouse_id']}",
        "--var", f"catalog={config['catalog']}",
        "--var", f"schema={config['schema']}",
        "--var", f"serving_endpoint={config['model']}",
    ]


def admin_pack(_: argparse.Namespace) -> int:
    config = _configured()
    request_dir = local_dir() / "admin-requests"
    request_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    host = str(config["workspace_host"])
    catalog = str(config["catalog"])
    schema = str(config["schema"])
    documents = {
        "account-admin.md": f"""# Account Admin 조건부 요청

대상 workspace: {host}

일반 설치에는 Account Admin 작업이 필요하지 않습니다. 다음 중 하나가 확인된 경우에만 요청합니다.

- Databricks Apps가 account/workspace 정책으로 차단되어 있습니다.
- App 생성에 필요한 account-level 기능 또는 정책 변경이 필요합니다.

해당하지 않으면 이 요청서는 무시해 주세요. 변경했다면 변경한 정책과 확인 시각을 회신해 주세요.
""",
        "workspace-admin.md": f"""# Workspace Admin / 리소스 owner 요청

대상 workspace: {host}

설치 principal에 이미 있는 권한은 다시 부여하지 말고, 실패한 항목만 최소 권한으로 적용해 주세요.

- Workspace access와 Job/App 생성 권한, serverless Jobs 사용 가능 여부
- 선택한 SQL warehouse: 설치 principal `CAN_USE` 및 App에 연결할 수 있는 공유/관리 권한
- 선택한 serving endpoint: analyzer principal `CAN_QUERY` 및 App에 연결할 수 있는 공유/관리 권한
- 감시할 고객 Job: watcher/analyzer principal `CAN_VIEW`
- 분석할 Notebook 또는 상위 directory: watcher/analyzer principal `CAN_READ`

Job/Notebook/warehouse/endpoint owner가 해당 권한을 줄 수 있으면 Workspace Admin 작업은 필요하지 않습니다. 적용 principal, object ID/path, permission과 검증 결과를 회신해 주세요.
""",
        "uc-admin.md": f"""# Catalog owner / Metastore Admin 요청

대상: `{catalog}.{schema}` 및 `{catalog}.demo`

신규 catalog를 설치자가 만들 경우 metastore `CREATE CATALOG`를 위임해 주세요. 관리자가 catalog/schema를 미리 만들 경우 설치 principal에 다음 최소 권한을 부여해 주세요.

- catalog: `USE CATALOG`
- schema `{schema}`와 `demo`: `USE SCHEMA`, `CREATE TABLE`, `SELECT`, `MODIFY`
- 설치자가 schema를 만들 경우 catalog: `CREATE SCHEMA`

App service principal은 App 생성 시 자동 생성되며 리포트 table `SELECT`가 Bundle 리소스로 연결됩니다. `system.lakeflow`와 `system.ai_gateway` 접근은 핵심 설치에는 필요하지 않으며 중앙 감사 확장을 요청한 경우에만 별도로 검토해 주세요.

적용 principal, securable, grant와 검증 결과를 회신해 주세요.
""",
    }
    for filename, contents in documents.items():
        path = request_dir / filename
        path.write_text(contents, encoding="utf-8")
        path.chmod(0o600)
        print(f"생성: {path}")
    print("\n다음 명령: ./setup.sh deploy")
    return 0


def deploy(args: argparse.Namespace) -> int:
    config = _configured()
    profile = str(config["profile"])
    bundle_vars = _bundle_vars(config)
    if not args.yes:
        if not sys.stdin.isatty() or input("Jobs, App, UC tables을 생성/갱신합니다. 계속할까요? [y/N] ").lower() not in {"y", "yes"}:
            print("배포를 취소했습니다.")
            return 1
    _run_checked(["databricks", "bundle", "validate", "--strict", "-t", args.target, *bundle_vars, "--profile", profile])
    _run_checked(["databricks", "bundle", "deploy", "-t", args.target, *bundle_vars, "--auto-approve", "--profile", profile])
    _run_checked(["databricks", "bundle", "run", "bootstrap", "-t", args.target, *bundle_vars, "--profile", profile])
    _run_checked(["databricks", "bundle", "run", "job_checker_app", "-t", args.target, *bundle_vars, "--profile", profile])
    save_json(state_path(), {"stage": "deployed", "target": args.target, "updated_at": datetime.now(timezone.utc).isoformat()})
    print("\n다음 명령: ./setup.sh verify")
    return 0


def resume(args: argparse.Namespace) -> int:
    print("저장된 설정으로 배포를 재개합니다.")
    return deploy(args)


def verify(args: argparse.Namespace) -> int:
    config = _configured()
    profile = str(config["profile"])
    bundle_vars = _bundle_vars(config)
    _run_checked(["databricks", "bundle", "summary", "-t", args.target, *bundle_vars, "--profile", profile])
    _run_checked(["databricks", "apps", "get", "ai-job-checker", "--profile", profile])
    statement = f"SELECT COUNT(*) AS watched_jobs FROM `{config['catalog']}`.`{config['schema']}`.`watched_jobs` WHERE enabled=true"
    _run_checked(["databricks", "experimental", "aitools", "tools", "query", statement, "--profile", profile])
    save_json(state_path(), {"stage": "verified", "target": args.target, "updated_at": datetime.now(timezone.utc).isoformat()})
    print("\n검증 완료. 다음 명령: ./setup.sh demo normal")
    return 0


def demo(args: argparse.Namespace) -> int:
    config = _configured()
    profile = str(config["profile"])
    bundle_vars = _bundle_vars(config)
    demo_command = ["databricks", "bundle", "run", "demo_ltv", "-t", args.target, *bundle_vars, "--params", f"scenario={args.scenario}", "--profile", profile]
    print(f"실행: {' '.join(demo_command)}")
    demo_result = subprocess.run(demo_command, check=False)
    if demo_result.returncode != 0 and args.scenario != "runtime_failure":
        raise RuntimeError(f"데모 Job이 예기치 않게 실패했습니다(exit {demo_result.returncode}).")
    if demo_result.returncode != 0:
        print("runtime_failure 시나리오의 의도된 Job 실패를 확인했습니다.")
    _run_checked(["databricks", "bundle", "run", "watcher", "-t", args.target, *bundle_vars, "--profile", profile])
    print("분석 Job이 비동기로 시작되었습니다. ./setup.sh verify로 상태를 확인하세요.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="setup.sh", description="Databricks AI Job Checker 설치 도우미")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="로컬 도구와 인증을 검사합니다.").set_defaults(handler=doctor)
    configure_parser = subparsers.add_parser("configure", help="배포 설정을 저장합니다.")
    configure_parser.add_argument("--profile")
    configure_parser.add_argument("--warehouse-id")
    configure_parser.add_argument("--catalog")
    configure_parser.add_argument("--schema")
    configure_parser.add_argument("--model")
    configure_parser.add_argument("--report-locale", choices=("ko", "en"))
    configure_parser.set_defaults(handler=configure)
    subparsers.add_parser("status", help="현재 단계와 다음 작업을 표시합니다.").set_defaults(handler=status)
    subparsers.add_parser("admin-pack", help="역할별 관리자 요청서를 생성합니다.").set_defaults(handler=admin_pack)
    for name, handler, help_text in (
        ("deploy", deploy, "DAB 리소스를 배포합니다."),
        ("resume", resume, "중단된 배포를 재개합니다."),
    ):
        command_parser = subparsers.add_parser(name, help=help_text)
        command_parser.add_argument("--target", default="nexon")
        command_parser.add_argument("--yes", action="store_true")
        command_parser.set_defaults(handler=handler)
    verify_parser = subparsers.add_parser("verify", help="배포와 데이터 접근을 검증합니다.")
    verify_parser.add_argument("--target", default="nexon")
    verify_parser.set_defaults(handler=verify)
    demo_parser = subparsers.add_parser("demo", help="데모 시나리오를 실행합니다.")
    demo_parser.add_argument("scenario", choices=("normal", "stale", "incomplete", "semantic_bug", "runtime_failure"))
    demo_parser.add_argument("--target", default="nexon")
    demo_parser.set_defaults(handler=demo)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (RuntimeError, ValueError) as error:
        print(f"오류: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
