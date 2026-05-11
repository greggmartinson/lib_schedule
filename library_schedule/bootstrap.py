from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence


def project_venv_python(project_root: Path) -> Path:
    return project_root / ".venv" / "bin" / "python"


def should_reexec_with_venv(
    project_root: Path,
    current_executable: str | Path | None = None,
) -> bool:
    venv_python = project_venv_python(project_root)
    if not venv_python.exists():
        return False

    executable = _absolute_path(current_executable or sys.executable)
    return executable != _absolute_path(venv_python)


def ensure_project_venv(
    script_path: str | Path,
    argv: Sequence[str] | None = None,
) -> None:
    script = Path(script_path).resolve()
    project_root = script.parent
    venv_python = project_venv_python(project_root)
    if not should_reexec_with_venv(project_root):
        return

    os.execv(
        str(venv_python),
        [str(venv_python), str(script), *(list(argv) if argv is not None else sys.argv[1:])],
    )


def _absolute_path(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(Path(path).expanduser())))
