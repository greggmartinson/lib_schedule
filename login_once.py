from __future__ import annotations

import argparse

from library_schedule.bootstrap import ensure_project_venv

ensure_project_venv(__file__)


def _missing_dependency_message(module_name: str) -> str:
    return (
        f"Missing dependency `{module_name}`.\n"
        "Install project dependencies in `.venv` with:\n"
        "  python3 -m venv .venv\n"
        "  .venv/bin/pip install -r requirements.txt\n"
        "  .venv/bin/playwright install chromium"
    )


try:
    from library_schedule.config import load_config
    from library_schedule.fetcher import BrowserLaunchError, login_once
except ModuleNotFoundError as exc:
    if exc.name in {"playwright", "yaml"}:
        raise SystemExit(_missing_dependency_message(exc.name)) from exc
    raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open browser for one-time authentication and save session."
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to YAML config file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config)
    try:
        login_once(config)
    except BrowserLaunchError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Saved authenticated session to: {config.auth_storage_state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
