from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup
from bs4.element import Tag

from .model import FetchedSchedulePage, PeriodRecord, ScheduleSummary


class ParseError(RuntimeError):
    pass


OPEN_MARKERS = {
    "",
    "-",
    "--",
    "open",
    "available",
    "none",
    "no reservation",
    "no reservations",
    "n/a",
}


def parse_schedule(
    html: str,
    target_spaces: list[str],
    room_aliases: dict[str, list[str]] | None = None,
    table_selector: str | None = None,
    report_date: date | None = None,
) -> ScheduleSummary:
    soup = BeautifulSoup(html, "html.parser")
    alias_lookup = _build_alias_lookup(target_spaces, room_aliases or {})

    table = _find_schedule_table(soup, alias_lookup, table_selector)
    if table is None:
        raise ParseError(
            "Could not find a table containing the target spaces. "
            "Set `schedule_table_selector` in config/settings.yaml to force a selector."
        )

    rows = _table_to_grid(table)
    header_row_idx, column_space_map = _find_header_mapping(rows, alias_lookup)
    if header_row_idx is None or not column_space_map:
        raise ParseError(
            "Found schedule-like table but could not map header columns to your spaces."
        )

    column_space_map = _repair_shifted_space_columns(rows, header_row_idx, column_space_map)
    period_col_idx = _guess_period_column(rows, header_row_idx, column_space_map)

    period_records: list[PeriodRecord] = []
    for row in rows[header_row_idx + 1 :]:
        if not any(_normalize(cell) for cell in row):
            continue

        period_label = _extract_period_label(row, period_col_idx)
        if not period_label:
            continue

        by_space: dict[str, str] = {}
        has_any_booking = False
        for col_idx, space in column_space_map.items():
            value = row[col_idx] if col_idx < len(row) else ""
            cleaned = _clean_booking_value(value)
            if cleaned:
                has_any_booking = True
            by_space[space] = cleaned

        if period_label and (has_any_booking or by_space):
            period_records.append(PeriodRecord(period_label=period_label, by_space=by_space))

    if not period_records:
        raise ParseError("No period rows were parsed from the selected schedule table.")

    normalized_spaces = _ordered_spaces(target_spaces)
    normalized_records = [
        PeriodRecord(
            period_label=record.period_label,
            by_space={space: record.by_space.get(space, "") for space in normalized_spaces},
        )
        for record in period_records
    ]
    return ScheduleSummary(
        report_date=report_date or datetime.now().date(),
        spaces=normalized_spaces,
        periods=normalized_records,
    )


def parse_schedule_pages(
    pages: list[FetchedSchedulePage],
    target_spaces: list[str],
    room_aliases: dict[str, list[str]] | None = None,
    table_selector: str | None = None,
    report_date: date | None = None,
) -> ScheduleSummary:
    resolved_date = report_date or datetime.now().date()
    if not pages:
        raise ParseError("No schedule pages were fetched.")

    if len(pages) == 1 and pages[0].room_name is None:
        return parse_schedule(
            html=pages[0].html,
            target_spaces=target_spaces,
            room_aliases=room_aliases,
            table_selector=table_selector,
            report_date=resolved_date,
        )

    room_summaries: list[ScheduleSummary] = []
    for page in pages:
        room_name = page.room_name
        if not room_name:
            continue
        room_summaries.append(
            _parse_room_day_schedule(
                html=page.html,
                room_name=room_name,
                report_date=resolved_date,
                table_selector=table_selector,
            )
        )

    if not room_summaries:
        raise ParseError("Fetched pages did not include any target room schedules.")

    return _merge_room_day_summaries(
        room_summaries=room_summaries,
        target_spaces=target_spaces,
        report_date=resolved_date,
    )


def _find_schedule_table(
    soup: BeautifulSoup,
    alias_lookup: dict[str, str],
    selector: str | None,
) -> Tag | None:
    tables = soup.select(selector) if selector else soup.find_all("table")
    if not tables:
        return None

    best_table: Tag | None = None
    best_score = -1
    for table in tables:
        rows = _table_to_grid(table)
        score = _table_score(rows, alias_lookup)
        if score > best_score:
            best_score = score
            best_table = table
    return best_table if best_score > 0 else None


def _find_room_day_table(
    soup: BeautifulSoup,
    report_date: date,
    selector: str | None,
) -> Tag | None:
    tables = soup.select(selector) if selector else soup.find_all("table")
    if not tables:
        return None

    best_table: Tag | None = None
    best_score = -1
    for table in tables:
        rows = _table_to_grid(table)
        score = _room_day_table_score(rows, report_date)
        if score > best_score:
            best_score = score
            best_table = table
    return best_table if best_score > 0 else None


def _table_score(rows: list[list[str]], alias_lookup: dict[str, str]) -> int:
    limit = min(8, len(rows))
    best = 0
    for idx in range(limit):
        matches = 0
        for cell in rows[idx]:
            if _match_space(cell, alias_lookup):
                matches += 1
        best = max(best, matches)
    return best


def _room_day_table_score(rows: list[list[str]], report_date: date) -> int:
    header_row_idx, day_col_idx = _find_report_day_column(rows, report_date)
    if header_row_idx is None or day_col_idx is None:
        return -1

    time_like_count = 0
    for row in rows[header_row_idx + 1 : header_row_idx + 13]:
        if row and _looks_like_time_or_period_label(row[0]):
            time_like_count += 1
    return 10 + time_like_count


def _find_header_mapping(
    rows: list[list[str]],
    alias_lookup: dict[str, str],
) -> tuple[int | None, dict[int, str]]:
    limit = min(8, len(rows))
    best_idx: int | None = None
    best_map: dict[int, str] = {}

    for idx in range(limit):
        current: dict[int, str] = {}
        for col_idx, cell in enumerate(rows[idx]):
            match = _match_space(cell, alias_lookup)
            if match:
                current[col_idx] = match
        if len(current) > len(best_map):
            best_map = current
            best_idx = idx
    return best_idx, best_map


def _find_report_day_column(
    rows: list[list[str]],
    report_date: date,
) -> tuple[int | None, int | None]:
    limit = min(6, len(rows))
    best_row_idx: int | None = None
    best_col_idx: int | None = None
    best_score = 0
    for row_idx in range(limit):
        for col_idx, cell in enumerate(rows[row_idx]):
            score = _report_day_header_score(cell, report_date)
            if score > best_score:
                best_score = score
                best_row_idx = row_idx
                best_col_idx = col_idx
    return best_row_idx, best_col_idx


def _repair_room_day_column(
    rows: list[list[str]],
    header_row_idx: int,
    day_col_idx: int,
) -> int:
    sample_rows = [
        row
        for row in rows[header_row_idx + 1 : header_row_idx + 8]
        if _extract_time_or_period_label(row)
    ]
    if not sample_rows:
        return day_col_idx

    max_cols = max((len(row) for row in sample_rows), default=0)
    candidate = day_col_idx
    while candidate < max_cols and _column_looks_like_time_labels(sample_rows, candidate):
        candidate += 1

    if candidate < max_cols:
        return candidate
    return day_col_idx


def _column_looks_like_time_labels(sample_rows: list[list[str]], col_idx: int) -> bool:
    matching_rows = 0
    populated_rows = 0
    for row in sample_rows:
        if col_idx >= len(row):
            continue
        label = _extract_time_or_period_label(row)
        cell_text = _clean_text(row[col_idx])
        if not label or not cell_text:
            continue
        populated_rows += 1
        if cell_text == label or _looks_like_time_or_period_label(cell_text):
            matching_rows += 1
    return populated_rows > 0 and matching_rows >= max(2, populated_rows // 2)


def _guess_period_column(
    rows: list[list[str]],
    header_row_idx: int,
    column_space_map: dict[int, str],
) -> int:
    if header_row_idx >= len(rows):
        return 0
    first_space_col = min(column_space_map.keys())
    if first_space_col > 0:
        return first_space_col - 1
    return 0


def _repair_shifted_space_columns(
    rows: list[list[str]],
    header_row_idx: int,
    column_space_map: dict[int, str],
) -> dict[int, str]:
    if not column_space_map:
        return column_space_map

    first_space_col = min(column_space_map)
    if first_space_col != 0:
        return column_space_map

    sample_rows = [
        row for row in rows[header_row_idx + 1 : header_row_idx + 7] if any(_normalize(cell) for cell in row)
    ]
    if not sample_rows:
        return column_space_map

    period_like_hits = 0
    for row in sample_rows:
        first_cell = row[0] if row else ""
        if _looks_like_period_label(first_cell):
            period_like_hits += 1

    if period_like_hits < max(2, len(sample_rows) // 2):
        return column_space_map

    shifted: dict[int, str] = {}
    max_cols = max((len(row) for row in sample_rows), default=0)
    for col_idx, space in column_space_map.items():
        next_idx = col_idx + 1
        if next_idx < max_cols:
            shifted[next_idx] = space

    return shifted or column_space_map


def _extract_period_label(row: list[str], period_col_idx: int) -> str:
    candidates = []
    if period_col_idx < len(row):
        candidates.append(row[period_col_idx])
    if row:
        candidates.append(row[0])

    for candidate in candidates:
        cleaned = _clean_text(candidate)
        if cleaned and _normalize(cleaned) not in OPEN_MARKERS:
            return cleaned
    return ""


def _extract_time_or_period_label(row: list[str]) -> str:
    if not row:
        return ""
    for candidate in row[:2]:
        cleaned = _clean_text(candidate)
        if cleaned and _looks_like_time_or_period_label(cleaned):
            return cleaned
    return ""


def _looks_like_period_label(text: str) -> bool:
    cleaned = _clean_text(text).lower()
    normalized = _normalize(text)
    if not normalized:
        return False
    period_markers = ("period", "lunch", "half")
    if any(marker in normalized for marker in period_markers):
        return True
    return bool(re.search(r"\b\d{1,2}:\d{2}\b", cleaned))


def _looks_like_time_or_period_label(text: str) -> bool:
    return _looks_like_period_label(text)


def _build_alias_lookup(
    target_spaces: list[str],
    room_aliases: dict[str, list[str]],
) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for space in target_spaces:
        aliases = room_aliases.get(space, [])
        if not aliases:
            aliases = [space]
        for alias in aliases:
            normalized = _normalize(alias)
            if normalized:
                lookup[normalized] = space
    return lookup


def _match_space(cell_text: str, alias_lookup: dict[str, str]) -> str | None:
    normalized = _normalize(cell_text)
    if not normalized:
        return None
    if normalized in alias_lookup:
        return alias_lookup[normalized]
    for alias, space in alias_lookup.items():
        if alias in normalized:
            return space
    return None


def _table_to_grid(table: Tag) -> list[list[str]]:
    rows: list[list[str]] = []
    pending: dict[tuple[int, int], str] = {}

    for row_idx, tr in enumerate(table.find_all("tr")):
        row: list[str] = []
        col_idx = 0

        while (row_idx, col_idx) in pending:
            row.append(pending[(row_idx, col_idx)])
            col_idx += 1

        for cell in tr.find_all(["th", "td"]):
            while (row_idx, col_idx) in pending:
                row.append(pending[(row_idx, col_idx)])
                col_idx += 1

            value = _clean_text(cell.get_text(" ", strip=True))
            rowspan = _safe_int(cell.get("rowspan"), default=1)
            colspan = _safe_int(cell.get("colspan"), default=1)

            for c in range(colspan):
                target_idx = col_idx + c
                while len(row) <= target_idx:
                    row.append("")
                row[target_idx] = value

                for r in range(1, rowspan):
                    pending[(row_idx + r, target_idx)] = value

            col_idx += colspan

        rows.append(row)

    max_cols = max((len(row) for row in rows), default=0)
    return [row + [""] * (max_cols - len(row)) for row in rows]


def _safe_int(raw: object, default: int) -> int:
    try:
        value = int(str(raw))
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _ordered_spaces(spaces: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in spaces:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _normalize(text: str) -> str:
    cleaned = _clean_text(text).lower()
    return re.sub(r"[^a-z0-9.]+", " ", cleaned).strip()


def _is_open_value(text: str) -> bool:
    return _clean_booking_value(text) == ""


def _clean_booking_value(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""

    stripped = cleaned
    stripped = re.sub(r"\breserve this time\b", " ", stripped, flags=re.IGNORECASE)
    stripped = re.sub(r"\bremove reservation\b", " ", stripped, flags=re.IGNORECASE)
    stripped = _clean_text(stripped)

    normalized = _normalize(stripped)
    if normalized in OPEN_MARKERS:
        return ""
    return stripped


def _matches_report_day_header(text: str, report_date: date) -> bool:
    return _report_day_header_score(text, report_date) > 0


def _report_day_header_score(text: str, report_date: date) -> int:
    cleaned = _clean_text(text).lower()
    normalized = _normalize(text)
    if not cleaned or not normalized:
        return 0

    weekday_full = report_date.strftime("%A").lower()
    weekday_short = report_date.strftime("%a").lower()
    numeric_date = f"{report_date.month}/{report_date.day}"
    zero_padded = report_date.strftime("%m/%d").lstrip("0").replace("/0", "/")

    score = 0
    if weekday_full in cleaned:
        score += 3
    elif weekday_short in cleaned:
        score += 2
    if numeric_date in cleaned or zero_padded in cleaned:
        score += 2
    return score


def _parse_room_day_schedule(
    html: str,
    room_name: str,
    report_date: date,
    table_selector: str | None,
) -> ScheduleSummary:
    soup = BeautifulSoup(html, "html.parser")
    table = _find_room_day_table(soup, report_date, table_selector)
    if table is None:
        raise ParseError(f"Could not find a day schedule table for {room_name}.")

    rows = _table_to_grid(table)
    header_row_idx, day_col_idx = _find_report_day_column(rows, report_date)
    if header_row_idx is None or day_col_idx is None:
        raise ParseError(f"Could not find the report day column for {room_name}.")
    day_col_idx = _repair_room_day_column(rows, header_row_idx, day_col_idx)

    period_records: list[PeriodRecord] = []
    for row in rows[header_row_idx + 1 :]:
        label = _extract_time_or_period_label(row)
        if not label:
            continue
        value = row[day_col_idx] if day_col_idx < len(row) else ""
        period_records.append(
            PeriodRecord(
                period_label=label,
                by_space={room_name: _clean_booking_value(value)},
            )
        )

    if not period_records:
        raise ParseError(f"No time rows were parsed for {room_name}.")

    return ScheduleSummary(
        report_date=report_date,
        spaces=[room_name],
        periods=period_records,
    )


def _merge_room_day_summaries(
    room_summaries: list[ScheduleSummary],
    target_spaces: list[str],
    report_date: date,
) -> ScheduleSummary:
    ordered_labels: list[str] = []
    label_seen: set[str] = set()
    merged: dict[str, dict[str, str]] = {}

    for summary in room_summaries:
        room_name = summary.spaces[0]
        for period in summary.periods:
            if period.period_label not in label_seen:
                label_seen.add(period.period_label)
                ordered_labels.append(period.period_label)
                merged[period.period_label] = {space: "" for space in target_spaces}
            merged[period.period_label][room_name] = period.by_space.get(room_name, "")

    return ScheduleSummary(
        report_date=report_date,
        spaces=_ordered_spaces(target_spaces),
        periods=[
            PeriodRecord(period_label=label, by_space=merged[label])
            for label in ordered_labels
        ],
    )
