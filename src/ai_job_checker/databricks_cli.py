from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


MINIMUM_VERSION = (0, 292, 0)


@dataclass(frozen=True)
class Profile:
    name: str
    host: str
    valid: bool


def run(*arguments: str, profile: str | None = None) -> subprocess.CompletedProcess[str]:
    command = ["databricks", *arguments]
    if profile is not None:
        command.extend(["--profile", profile])
    return subprocess.run(command, text=True, capture_output=True, check=False)


def parse_version(output: str) -> tuple[int, int, int] | None:
    match = re.search(r"(?:v)?(\d+)\.(\d+)(?:\.(\d+))?", output)
    if not match:
        return None
    return tuple(int(part or 0) for part in match.groups())  # type: ignore[return-value]


def list_profiles() -> list[Profile]:
    result = run("auth", "profiles")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to list Databricks profiles")

    profiles: list[Profile] = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("name "):
            continue
        columns = stripped.split()
        if len(columns) >= 2:
            profiles.append(Profile(columns[0], columns[1], columns[-1].lower() == "yes"))
    return profiles

