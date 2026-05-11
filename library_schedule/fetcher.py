from __future__ import annotations

from dataclasses import dataclass
import time
import re
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

from .config import AppConfig
from .model import FetchedSchedulePage


class AuthRequiredError(RuntimeError):
    pass


@dataclass(frozen=True)
class _RoomSelectorMatch:
    index: int
    room_option_values: dict[str, str]


@dataclass(frozen=True)
class _RoomLinkTarget:
    room_name: str
    href: str


def login_once(config: AppConfig) -> None:
    storage_path = config.auth_storage_state_path
    storage_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(config.schedule_url, timeout=config.browser_timeout_ms)
        page.wait_for_timeout(1000)

        if not _looks_like_schedule_page(page.url, page.content(), config):
            print("\nComplete login in the browser window. This script will continue automatically.")
            _wait_for_authenticated_schedule_page(page, config)

        context.storage_state(path=str(storage_path))
        browser.close()


def fetch_schedule_html(
    config: AppConfig,
    headless: bool | None = None,
) -> tuple[str, str]:
    pages = fetch_schedule_pages(config, headless=headless)
    first_page = pages[0]
    return first_page.html, first_page.final_url


def fetch_schedule_pages(
    config: AppConfig,
    headless: bool | None = None,
) -> list[FetchedSchedulePage]:
    storage_path = config.auth_storage_state_path
    if not storage_path.exists():
        raise AuthRequiredError(
            f"Missing auth session file at {storage_path}. "
            "Run login_once.py first."
        )

    use_headless = config.default_headless if headless is None else headless
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=use_headless)
        context = browser.new_context(storage_state=str(storage_path))
        page = context.new_page()
        page.goto(config.schedule_url, timeout=config.browser_timeout_ms)
        page.wait_for_timeout(1200)
        room_selector = _find_room_selector(page, config)
        if room_selector:
            pages = _capture_room_pages(page, config, room_selector)
        else:
            room_links = _find_room_links(page, config)
            if room_links:
                pages = _capture_room_link_pages(page, config, room_links)
            else:
                pages = [FetchedSchedulePage(room_name=None, html=page.content(), final_url=page.url)]
        browser.close()

    if any(_looks_like_login_page(item.html) for item in pages):
        raise AuthRequiredError(
            "Stored session appears to be expired. Re-run login_once.py."
        )

    return pages


def _looks_like_login_page(html: str) -> bool:
    lower = html.lower()
    login_markers = (
        "type=\"password\"",
        "name=\"password\"",
        "name=\"passwd\"",
        "sign in",
        "log in",
    )
    return any(marker in lower for marker in login_markers)


def _wait_for_authenticated_schedule_page(page, config: AppConfig) -> None:
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        page.wait_for_timeout(1000)
        if page.is_closed():
            raise AuthRequiredError("Login browser window was closed before authentication completed.")

        html = page.content()
        if _looks_like_schedule_page(page.url, html, config):
            return

    raise AuthRequiredError("Timed out waiting for login to complete in the browser.")


def _looks_like_schedule_page(url: str, html: str, config: AppConfig) -> bool:
    if _looks_like_login_page(html):
        return False

    lower_url = url.lower()
    lower_html = html.lower()
    if "computerlab/reserve" in lower_url or "picklab.cfm" in lower_url:
        return True

    schedule_markers = [
        "reserve this time",
        "remove reservation",
        "period/time",
    ]
    if any(marker in lower_html for marker in schedule_markers):
        return True

    alias_hits = 0
    for aliases in config.room_aliases.values():
        for alias in aliases:
            normalized = alias.strip().lower()
            if normalized and normalized in lower_html:
                alias_hits += 1
                if alias_hits >= 2:
                    return True
    return False


def _find_room_selector(page, config: AppConfig) -> _RoomSelectorMatch | None:
    selects = page.locator("select")
    select_count = selects.count()
    best_match: _RoomSelectorMatch | None = None

    for index in range(select_count):
        locator = selects.nth(index)
        options = locator.locator("option").evaluate_all(
            """
            (nodes) => nodes.map((node) => ({
              value: node.value || "",
              text: (node.textContent || "").trim()
            }))
            """
        )
        room_option_values = _match_room_options(
            options=options,
            target_spaces=config.target_spaces,
            room_aliases=config.room_aliases,
        )
        if len(room_option_values) < 2:
            continue
        if best_match is None or len(room_option_values) > len(best_match.room_option_values):
            best_match = _RoomSelectorMatch(
                index=index,
                room_option_values=room_option_values,
            )

    return best_match


def _match_room_options(
    options: list[dict[str, str]],
    target_spaces: list[str],
    room_aliases: dict[str, list[str]],
) -> dict[str, str]:
    matched: dict[str, str] = {}
    for space in target_spaces:
        aliases = room_aliases.get(space, []) or [space]
        option = _find_option_for_aliases(options, aliases)
        if option:
            matched[space] = option["value"]
    return matched


def _find_option_for_aliases(
    options: list[dict[str, str]],
    aliases: list[str],
) -> dict[str, str] | None:
    normalized_aliases = [_normalize_label(alias) for alias in aliases if alias.strip()]
    for alias in normalized_aliases:
        for option in options:
            if _normalize_label(option["text"]) == alias:
                return option
    for alias in normalized_aliases:
        for option in options:
            option_text = _normalize_label(option["text"])
            if alias and (alias in option_text or option_text in alias):
                return option
    return None


def _capture_room_pages(
    page,
    config: AppConfig,
    room_selector: _RoomSelectorMatch,
) -> list[FetchedSchedulePage]:
    pages: list[FetchedSchedulePage] = []
    for room_name in config.target_spaces:
        option_value = room_selector.room_option_values.get(room_name)
        if option_value is None:
            continue
        _select_room(page, room_selector.index, option_value, config.browser_timeout_ms)
        pages.append(
            FetchedSchedulePage(
                room_name=room_name,
                html=page.content(),
                final_url=page.url,
            )
        )
    return pages


def _find_room_links(page, config: AppConfig) -> list[_RoomLinkTarget]:
    anchors = page.locator("a")
    anchor_count = anchors.count()
    discovered: list[dict[str, str]] = []

    for index in range(anchor_count):
        anchor = anchors.nth(index)
        try:
            text = (anchor.text_content() or "").strip()
            href = anchor.get_attribute("href") or ""
        except Exception:  # noqa: BLE001
            continue
        if not text and not href:
            continue
        discovered.append({"text": text, "href": href})

    matches: list[_RoomLinkTarget] = []
    for room_name in config.target_spaces:
        aliases = config.room_aliases.get(room_name, []) or [room_name]
        match = _find_link_for_aliases(discovered, aliases, page.url)
        if match:
            matches.append(_RoomLinkTarget(room_name=room_name, href=match))
    return matches


def _find_link_for_aliases(
    anchors: list[dict[str, str]],
    aliases: list[str],
    base_url: str,
) -> str | None:
    normalized_aliases = [_normalize_label(alias) for alias in aliases if alias.strip()]
    for alias in normalized_aliases:
        for anchor in anchors:
            text = _normalize_label(anchor.get("text", ""))
            if text == alias:
                return urljoin(base_url, anchor.get("href", ""))
    for alias in normalized_aliases:
        for anchor in anchors:
            text = _normalize_label(anchor.get("text", ""))
            if alias and text and (alias in text or text in alias):
                return urljoin(base_url, anchor.get("href", ""))
    return None


def _capture_room_link_pages(
    page,
    config: AppConfig,
    room_links: list[_RoomLinkTarget],
) -> list[FetchedSchedulePage]:
    pages: list[FetchedSchedulePage] = []
    for target in room_links:
        page.goto(target.href, timeout=config.browser_timeout_ms)
        page.wait_for_timeout(1200)
        pages.append(
            FetchedSchedulePage(
                room_name=target.room_name,
                html=page.content(),
                final_url=page.url,
            )
        )
    return pages


def _select_room(page, selector_index: int, option_value: str, timeout_ms: int) -> None:
    locator = page.locator("select").nth(selector_index)
    locator.select_option(value=option_value)
    try:
        locator.dispatch_event("change")
    except Exception:  # noqa: BLE001
        pass
    try:
        page.wait_for_load_state("networkidle", timeout=min(timeout_ms, 4000))
    except Exception:  # noqa: BLE001
        pass
    page.wait_for_timeout(1200)


def _normalize_label(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    return " ".join(cleaned.split())
