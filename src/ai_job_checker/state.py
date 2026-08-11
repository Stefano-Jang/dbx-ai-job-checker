from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


SENSITIVE_KEYS = {"token", "password", "secret", "client_secret", "access_token"}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def local_dir() -> Path:
    return Path(os.environ.get("AI_JOB_CHECKER_LOCAL_DIR", project_root() / ".local"))


def config_path() -> Path:
    return local_dir() / "config.json"


def state_path() -> Path:
    return local_dir() / "setup-state.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _assert_no_secrets(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS or normalized.endswith("_token"):
                raise ValueError(f"Refusing to persist sensitive field: {path}.{key}")
            _assert_no_secrets(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_no_secrets(child, f"{path}[{index}]")


def save_json(path: Path, value: dict[str, Any]) -> None:
    _assert_no_secrets(value)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise

