from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta, timezone
import re
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import IcsCalendarConfig
from .model import CalendarAgenda, CalendarEvent


class CalendarFeedError(RuntimeError):
    pass


def fetch_calendar_agenda(
    config: IcsCalendarConfig,
    report_date: date,
) -> CalendarAgenda:
    try:
        local_tz = ZoneInfo(config.timezone)
    except ZoneInfoNotFoundError as exc:
        raise CalendarFeedError(f"Unknown calendar timezone: {config.timezone}") from exc

    ics_text = _fetch_ics_text(config.url)
    return parse_calendar_agenda(
        ics_text=ics_text,
        report_date=report_date,
        local_tz=local_tz,
        display_name=config.display_name,
    )


def build_unavailable_calendar_agenda(
    config: IcsCalendarConfig,
    report_date: date,
    status_note: str = "Calendar feed unavailable.",
) -> CalendarAgenda:
    source_name = (config.display_name or "Calendar").strip() or "Calendar"
    return CalendarAgenda(
        report_date=report_date,
        source_name=source_name,
        events=[],
        status_note=status_note,
    )


def fetch_calendar_agenda_bundle(
    configs: Sequence[IcsCalendarConfig],
    report_date: date,
) -> tuple[CalendarAgenda | None, list[str]]:
    active_configs = [config for config in configs if config.url.strip()]
    if not active_configs:
        return None, []

    if len(active_configs) == 1:
        config = active_configs[0]
        try:
            return fetch_calendar_agenda(config, report_date), []
        except CalendarFeedError as exc:
            return (
                build_unavailable_calendar_agenda(config, report_date),
                [_format_feed_warning(config, exc)],
            )

    agendas: list[CalendarAgenda] = []
    warnings: list[str] = []
    for config in active_configs:
        try:
            agendas.append(fetch_calendar_agenda(config, report_date))
        except CalendarFeedError as exc:
            warnings.append(_format_feed_warning(config, exc))

    if agendas:
        return combine_calendar_agendas(
            agendas,
            source_name=_derive_combined_source_name(active_configs),
        ), warnings

    checked_sources = ", ".join(
        _short_source_name(config.display_name or "") for config in active_configs
    )
    return (
        CalendarAgenda(
            report_date=report_date,
            source_name=_derive_combined_source_name(active_configs),
            events=[],
            status_note=(
                "Calendar feeds unavailable."
                if not checked_sources
                else f"Calendar feeds unavailable. Checked: {checked_sources}."
            ),
        ),
        warnings,
    )


def parse_calendar_agenda(
    ics_text: str,
    report_date: date,
    local_tz: ZoneInfo,
    display_name: str | None = None,
) -> CalendarAgenda:
    calendar_name = ""
    event_props: dict[str, tuple[dict[str, str], str]] | None = None
    parsed_events: list[_ParsedEvent] = []

    for line in _unfold_ics_lines(ics_text):
        if not line:
            continue

        upper_line = line.upper()
        if upper_line == "BEGIN:VEVENT":
            event_props = {}
            continue
        if upper_line == "END:VEVENT":
            if event_props is not None:
                parsed_event = _build_parsed_event(event_props, report_date, local_tz)
                if parsed_event is not None:
                    parsed_events.append(parsed_event)
            event_props = None
            continue

        try:
            name, params, value = _parse_property_line(line)
        except ValueError:
            continue

        if event_props is not None:
            event_props[name] = (params, value)
        elif name == "X-WR-CALNAME":
            calendar_name = _clean_whitespace(_unescape_ics_text(value))

    source_name = _derive_source_name(display_name, calendar_name)
    parsed_events.sort(key=lambda item: (item.sort_key, item.title.lower()))
    return CalendarAgenda(
        report_date=report_date,
        source_name=source_name,
        events=[
            CalendarEvent(
                title=item.title,
                when=item.when,
                details=item.details,
                sort_key=item.sort_key.isoformat(),
            )
            for item in parsed_events
        ],
    )


def combine_calendar_agendas(
    agendas: Sequence[CalendarAgenda],
    source_name: str | None = None,
) -> CalendarAgenda:
    if not agendas:
        raise ValueError("At least one calendar agenda is required to combine.")

    if len(agendas) == 1 and (source_name is None or source_name == agendas[0].source_name):
        return agendas[0]

    combined_source = source_name or agendas[0].source_name
    combined_events: list[CalendarEvent] = []
    checked_sources: list[str] = []

    for agenda in agendas:
        short_source = _short_source_name(agenda.source_name)
        if short_source:
            checked_sources.append(short_source)

        for event in agenda.events:
            detail_parts = []
            if short_source:
                detail_parts.append(short_source)
            if event.details:
                detail_parts.append(event.details)
            combined_events.append(
                CalendarEvent(
                    title=event.title,
                    when=event.when,
                    details=" | ".join(detail_parts) or None,
                    sort_key=event.sort_key,
                )
            )

    combined_events.sort(
        key=lambda event: (
            event.sort_key or "",
            event.title.lower(),
            (event.details or "").lower(),
        )
    )

    status_note = None
    if not combined_events and checked_sources:
        status_note = f"No calendar events today. Checked: {', '.join(checked_sources)}."

    return CalendarAgenda(
        report_date=agendas[0].report_date,
        source_name=combined_source,
        events=combined_events,
        status_note=status_note,
    )


class _ParsedEvent:
    def __init__(self, title: str, when: str, sort_key: datetime, details: str | None) -> None:
        self.title = title
        self.when = when
        self.sort_key = sort_key
        self.details = details


def _fetch_ics_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "LibrarySchedule/1.0",
            "Accept": "text/calendar,text/plain;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with urlopen(request, timeout=30, context=_build_ssl_context()) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise CalendarFeedError(f"Unable to load ICS calendar feed: {exc}") from exc


def _build_ssl_context() -> ssl.SSLContext:
    cafile: str | None = None
    try:
        import certifi
    except ModuleNotFoundError:
        certifi = None

    if certifi is not None:
        cafile = certifi.where()

    if cafile:
        return ssl.create_default_context(cafile=cafile)
    return ssl.create_default_context()


def _unfold_ics_lines(ics_text: str) -> list[str]:
    unfolded: list[str] = []
    for raw_line in ics_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw_line.startswith((" ", "\t")) and unfolded:
            unfolded[-1] += raw_line[1:]
            continue
        unfolded.append(raw_line)
    return unfolded


def _parse_property_line(line: str) -> tuple[str, dict[str, str], str]:
    left, value = line.split(":", maxsplit=1)
    segments = left.split(";")
    name = segments[0].upper()
    params: dict[str, str] = {}
    for segment in segments[1:]:
        if "=" not in segment:
            continue
        param_name, param_value = segment.split("=", maxsplit=1)
        params[param_name.upper()] = param_value
    return name, params, value


def _build_parsed_event(
    event_props: dict[str, tuple[dict[str, str], str]],
    report_date: date,
    local_tz: ZoneInfo,
) -> _ParsedEvent | None:
    raw_summary = _property_value(event_props, "SUMMARY")
    summary = _clean_calendar_title(raw_summary)
    if not summary:
        return None

    status = _clean_whitespace(_unescape_ics_text(_property_value(event_props, "STATUS")))
    if status.upper() == "CANCELLED" or raw_summary.upper().startswith("CANCELLED:"):
        return None

    start = _parse_ics_datetime(event_props, "DTSTART", local_tz)
    end = _parse_ics_datetime(event_props, "DTEND", local_tz)
    if start is None:
        return None

    start_dt, is_all_day = start
    if end is None:
        end_dt = start_dt + (timedelta(days=1) if is_all_day else timedelta(hours=1))
    else:
        end_dt = end[0]
    if end_dt <= start_dt:
        end_dt = start_dt + (timedelta(days=1) if is_all_day else timedelta(hours=1))

    day_start = datetime.combine(report_date, time.min, tzinfo=local_tz)
    day_end = day_start + timedelta(days=1)
    if end_dt <= day_start or start_dt >= day_end:
        return None

    description = _clean_whitespace(_unescape_ics_text(_property_value(event_props, "DESCRIPTION")))
    details = description or None
    return _ParsedEvent(
        title=summary,
        when=_format_event_time(start_dt, end_dt, report_date, is_all_day=is_all_day),
        sort_key=start_dt,
        details=details,
    )


def _parse_ics_datetime(
    event_props: dict[str, tuple[dict[str, str], str]],
    key: str,
    default_tz: ZoneInfo,
) -> tuple[datetime, bool] | None:
    prop = event_props.get(key)
    if prop is None:
        return None

    params, raw_value = prop
    value = raw_value.strip()
    if not value:
        return None

    if params.get("VALUE", "").upper() == "DATE" or re.fullmatch(r"\d{8}", value):
        parsed_date = datetime.strptime(value, "%Y%m%d").date()
        return datetime.combine(parsed_date, time.min, tzinfo=default_tz), True

    tz_name = params.get("TZID", "").strip()
    tzinfo = default_tz
    if tz_name:
        try:
            tzinfo = ZoneInfo(tz_name)
        except ZoneInfoNotFoundError:
            tzinfo = default_tz

    aware_dt: datetime | None = None
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if value.endswith("Z"):
            aware_dt = parsed.replace(tzinfo=timezone.utc).astimezone(default_tz)
        else:
            aware_dt = parsed.replace(tzinfo=tzinfo).astimezone(default_tz)
        break

    if aware_dt is None:
        return None
    return aware_dt, False


def _property_value(
    event_props: dict[str, tuple[dict[str, str], str]],
    key: str,
) -> str:
    prop = event_props.get(key)
    if prop is None:
        return ""
    return prop[1]


def _clean_calendar_title(value: str) -> str:
    cleaned = _clean_whitespace(_unescape_ics_text(value))
    if not cleaned:
        return ""
    cleaned = re.sub(r"^\d{2,4}-\d+:\s*", "", cleaned)
    return cleaned.strip()


def _format_event_time(
    start_dt: datetime,
    end_dt: datetime,
    report_date: date,
    is_all_day: bool,
) -> str:
    if is_all_day:
        return "All day"

    starts_today = start_dt.date() == report_date
    ends_today = end_dt.date() == report_date

    if starts_today and ends_today:
        return f"{_format_clock(start_dt)} - {_format_clock(end_dt)}"
    if starts_today and not ends_today:
        return f"{_format_clock(start_dt)} - Late"
    if not starts_today and ends_today:
        return f"Until {_format_clock(end_dt)}"
    return "Multi-day"


def _format_clock(value: datetime) -> str:
    text = value.strftime("%I:%M %p")
    if text.startswith("0"):
        text = text[1:]
    if text.endswith(":00 AM") or text.endswith(":00 PM"):
        text = text.replace(":00 ", " ")
    return text


def _derive_source_name(display_name: str | None, calendar_name: str) -> str:
    if display_name and display_name.strip():
        return display_name.strip()
    if not calendar_name:
        return "Calendar"
    shortened = calendar_name.split(":")[-1].strip()
    return shortened or "Calendar"


def _derive_combined_source_name(configs: Sequence[IcsCalendarConfig]) -> str:
    display_names = [
        config.display_name.strip()
        for config in configs
        if config.display_name and config.display_name.strip()
    ]
    if not display_names:
        return "Calendar"
    if len(display_names) == 1:
        return display_names[0]
    if sum("media center" in name.lower() for name in display_names) >= max(1, len(display_names) // 2):
        return "Media Center"
    return "Calendar"


def _format_feed_warning(config: IcsCalendarConfig, exc: CalendarFeedError) -> str:
    source_name = _describe_feed_source(config)
    if not source_name:
        return str(exc)
    return f"{source_name}: {exc}"


def _describe_feed_source(config: IcsCalendarConfig) -> str:
    if config.display_name and config.display_name.strip():
        return config.display_name.strip()
    return config.url.strip()


def _short_source_name(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""

    parts = re.split(r"\s[–-]\s|:", cleaned, maxsplit=1)
    if len(parts) == 2:
        head, tail = parts[0].strip(), parts[1].strip()
        if tail.lower() == "media center" and head:
            return head
        if tail:
            return tail
    return cleaned


def _unescape_ics_text(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _clean_whitespace(value: str) -> str:
    return " ".join(value.split())
