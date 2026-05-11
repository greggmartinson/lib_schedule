from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


DEFAULT_SPACES = [
    "MC C220.6",
    "MC C220.7",
    "MC C220.9",
    "MC Center",
    "MC Lab North",
    "MC Lab South",
    "MC Minneapolis",
    "MC St. Paul",
]


@dataclass(frozen=True)
class GoogleSlidesConfig:
    presentation_url: str
    slide_index: int
    oauth_client_secret_path: Path
    oauth_token_path: Path
    apps_script_web_app_url: str | None


@dataclass(frozen=True)
class IcsCalendarConfig:
    url: str
    timezone: str
    display_name: str | None


@dataclass(frozen=True)
class AppConfig:
    schedule_url: str
    target_spaces: list[str]
    room_aliases: dict[str, list[str]]
    schedule_table_selector: str | None
    drop_first_period_rows: int
    drop_last_period_rows: int
    auth_storage_state_path: Path
    browser_timeout_ms: int
    default_headless: bool
    google_slides: GoogleSlidesConfig | None
    ics_calendars: list[IcsCalendarConfig]


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    schedule_url = raw.get("schedule_url", "").strip()
    if not schedule_url:
        raise ValueError("config.schedule_url is required")

    target_spaces = _clean_list(raw.get("target_spaces")) or list(DEFAULT_SPACES)
    room_aliases = _clean_alias_map(raw.get("room_aliases"), target_spaces)
    auth = raw.get("auth", {})

    storage_state = auth.get("storage_state_path", ".auth/storage_state.json")
    drop_first = max(0, int(raw.get("drop_first_period_rows", 0)))
    drop_last = max(0, int(raw.get("drop_last_period_rows", 0)))
    timeout_ms = int(raw.get("browser_timeout_ms", 45000))
    default_headless = bool(raw.get("default_headless", True))
    google_slides = _load_google_slides_config(raw.get("google_slides"))
    ics_calendars = _load_ics_calendar_configs(raw)

    return AppConfig(
        schedule_url=schedule_url,
        target_spaces=target_spaces,
        room_aliases=room_aliases,
        schedule_table_selector=raw.get("schedule_table_selector"),
        drop_first_period_rows=drop_first,
        drop_last_period_rows=drop_last,
        auth_storage_state_path=Path(storage_state),
        browser_timeout_ms=timeout_ms,
        default_headless=default_headless,
        google_slides=google_slides,
        ics_calendars=ics_calendars,
    )


def _clean_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            items.append(text)
    return items


def _clean_alias_map(value: object, spaces: list[str]) -> dict[str, list[str]]:
    aliases: dict[str, list[str]] = {space: [space] for space in spaces}
    if not isinstance(value, dict):
        return aliases

    for space in spaces:
        raw_items = value.get(space, [])
        if not isinstance(raw_items, list):
            continue
        for alias in raw_items:
            text = str(alias).strip()
            if text and text not in aliases[space]:
                aliases[space].append(text)
    return aliases


def _load_google_slides_config(value: object) -> GoogleSlidesConfig | None:
    if not isinstance(value, dict):
        return None

    presentation_url = str(value.get("presentation_url", "")).strip()
    if not presentation_url:
        return None

    slide_index = max(1, int(value.get("slide_index", 2)))
    client_secret_path = Path(
        str(value.get("oauth_client_secret_path", "config/google_oauth_client_secret.json"))
    )
    token_path = Path(str(value.get("oauth_token_path", ".auth/google_slides_token.json")))
    web_app_url = str(value.get("apps_script_web_app_url", "")).strip() or None

    return GoogleSlidesConfig(
        presentation_url=presentation_url,
        slide_index=slide_index,
        oauth_client_secret_path=client_secret_path,
        oauth_token_path=token_path,
        apps_script_web_app_url=web_app_url,
    )


def _load_ics_calendar_config(value: object) -> IcsCalendarConfig | None:
    if not isinstance(value, dict):
        return None

    url = str(value.get("url", "")).strip()
    if not url:
        return None

    timezone = str(value.get("timezone", "America/Chicago")).strip() or "America/Chicago"
    display_name = str(value.get("display_name", "")).strip() or None
    return IcsCalendarConfig(
        url=url,
        timezone=timezone,
        display_name=display_name,
    )


def _load_ics_calendar_configs(raw: dict[str, object]) -> list[IcsCalendarConfig]:
    configs: list[IcsCalendarConfig] = []

    multi_value = raw.get("ics_calendars")
    if isinstance(multi_value, list):
        for item in multi_value:
            config = _load_ics_calendar_config(item)
            if config is not None:
                configs.append(config)
        if configs:
            return configs

    single_value = raw.get("ics_calendar")
    config = _load_ics_calendar_config(single_value)
    if config is not None:
        configs.append(config)
    return configs
