from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from pathlib import Path
from uuid import uuid4

from .booking_text import clean_booking_for_display
from .config import GoogleSlidesConfig
from .model import CalendarAgenda, CondensedScheduleSummary, SummaryEntry


GOOGLE_SLIDES_SCOPES = ["https://www.googleapis.com/auth/presentations"]
EMU_PER_PT = 12700
SLIDE_EVENT_LIMIT = 4


@dataclass(frozen=True)
class SlideSyncResult:
    presentation_id: str
    slide_index: int
    slide_object_id: str
    title: str


def sync_condensed_summary_to_slide(
    summary: CondensedScheduleSummary,
    config: GoogleSlidesConfig,
    calendar_agenda: CalendarAgenda | None = None,
) -> SlideSyncResult:
    credentials = _get_google_credentials(config)
    service = _build_slides_service(credentials)
    presentation_id = extract_presentation_id(config.presentation_url)
    presentation = service.presentations().get(presentationId=presentation_id).execute()

    slides = presentation.get("slides", [])
    if config.slide_index > len(slides):
        raise ValueError(
            f"Presentation only has {len(slides)} slides, but config requests slide {config.slide_index}."
        )

    slide = slides[config.slide_index - 1]
    requests = build_slide_update_requests(
        slide=slide,
        summary=summary,
        page_size=presentation.get("pageSize", {}),
        calendar_agenda=calendar_agenda,
    )
    service.presentations().batchUpdate(
        presentationId=presentation_id,
        body={"requests": requests},
    ).execute()

    return SlideSyncResult(
        presentation_id=presentation_id,
        slide_index=config.slide_index,
        slide_object_id=slide["objectId"],
        title=presentation.get("title", "Untitled presentation"),
    )


def extract_presentation_id(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("Google presentation URL or ID is required.")

    match = re.search(r"/presentation/d/([a-zA-Z0-9_-]+)", cleaned)
    if match:
        return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", cleaned):
        return cleaned
    raise ValueError("Could not extract Google presentation ID from the configured value.")


def build_slide_update_requests(
    slide: dict,
    summary: CondensedScheduleSummary,
    page_size: dict,
    calendar_agenda: CalendarAgenda | None = None,
) -> list[dict]:
    slide_id = slide["objectId"]
    existing_elements = slide.get("pageElements", [])
    requests: list[dict] = [
        {"deleteObject": {"objectId": element["objectId"]}}
        for element in existing_elements
    ]

    page_width_pt = _dimension_to_pt(page_size.get("width"), default=960)
    page_height_pt = _dimension_to_pt(page_size.get("height"), default=540)

    title_box = _textbox_request(
        page_id=slide_id,
        object_id=_new_object_id("schedule_title"),
        left=28,
        top=18,
        width=page_width_pt - 56,
        height=52,
        text=_build_title_text(summary),
        font_size=24,
        bold_range=(0, len("Library Spaces Summary")),
    )
    requests.extend(title_box)

    card_requests = _build_room_card_requests(
        slide_id=slide_id,
        summary=summary,
        page_width_pt=page_width_pt,
        page_height_pt=page_height_pt,
        calendar_agenda=calendar_agenda,
    )
    requests.extend(card_requests)
    return requests


def format_room_card_text(room_name: str, entries: list[SummaryEntry]) -> str:
    if not entries:
        return f"{room_name}\nFree all day"

    parts = [room_name]
    for entry in entries:
        parts.append(clean_booking_for_display(entry.booking))
        parts.append(entry.when)
        parts.append("")
    return "\n".join(parts).rstrip()


def format_calendar_card_text(
    agenda: CalendarAgenda,
    max_events: int = SLIDE_EVENT_LIMIT,
) -> str:
    heading = f"{agenda.source_name} Events"
    if agenda.status_note:
        return f"{heading}\n{agenda.status_note}"
    if not agenda.events:
        return f"{heading}\nNo calendar events today."

    parts = [heading]
    for event in agenda.events[:max_events]:
        parts.append(event.title)
        detail_line = event.when
        if event.details:
            detail_line = f"{detail_line} | {event.details}"
        parts.append(detail_line)
        parts.append("")
    remaining = len(agenda.events) - max_events
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return "\n".join(parts).rstrip()


def _build_title_text(summary: CondensedScheduleSummary) -> str:
    date_text = summary.report_date.strftime("%A, %B %-d, %Y")
    generated_text = datetime.now().strftime("Generated %I:%M %p").lstrip("0")
    return f"Library Spaces Summary\n{date_text} | {generated_text}"


def _build_room_card_requests(
    slide_id: str,
    summary: CondensedScheduleSummary,
    page_width_pt: float,
    page_height_pt: float,
    calendar_agenda: CalendarAgenda | None = None,
) -> list[dict]:
    columns = 4 if calendar_agenda is None else 3
    gutter = 12
    margin_x = 28
    top = 88
    bottom_margin = 26
    cards = [
        (
            room_name,
            format_room_card_text(room_name, summary.by_space.get(room_name, [])),
        )
        for room_name in summary.spaces
    ]
    if calendar_agenda is not None:
        cards.append(
            (
                f"{calendar_agenda.source_name} Events",
                format_calendar_card_text(calendar_agenda),
            )
        )

    rows = max(1, (len(cards) + columns - 1) // columns)
    usable_width = page_width_pt - (margin_x * 2) - (gutter * (columns - 1))
    card_width = usable_width / columns
    usable_height = page_height_pt - top - bottom_margin - (gutter * max(rows - 1, 0))
    card_height = usable_height / rows

    requests: list[dict] = []
    for index, (card_title, card_text) in enumerate(cards):
        col = index % columns
        row = index // columns
        left = margin_x + col * (card_width + gutter)
        top_pos = top + row * (card_height + gutter)
        object_id = _new_object_id(f"room_{index + 1}")
        bold_range = (0, len(card_title))
        requests.extend(
            _textbox_request(
                page_id=slide_id,
                object_id=object_id,
                left=left,
                top=top_pos,
                width=card_width,
                height=card_height,
                text=card_text,
                font_size=13,
                bold_range=bold_range,
            )
        )
    return requests


def _textbox_request(
    page_id: str,
    object_id: str,
    left: float,
    top: float,
    width: float,
    height: float,
    text: str,
    font_size: int,
    bold_range: tuple[int, int] | None = None,
) -> list[dict]:
    requests = [
        {
            "createShape": {
                "objectId": object_id,
                "shapeType": "TEXT_BOX",
                "elementProperties": {
                    "pageObjectId": page_id,
                    "size": {
                        "width": {"magnitude": width, "unit": "PT"},
                        "height": {"magnitude": height, "unit": "PT"},
                    },
                    "transform": {
                        "scaleX": 1,
                        "scaleY": 1,
                        "translateX": left,
                        "translateY": top,
                        "unit": "PT",
                    },
                },
            }
        },
        {"insertText": {"objectId": object_id, "text": text}},
        {
            "updateTextStyle": {
                "objectId": object_id,
                "style": {"fontSize": {"magnitude": font_size, "unit": "PT"}},
                "textRange": {"type": "ALL"},
                "fields": "fontSize",
            }
        },
    ]
    if bold_range:
        requests.append(
            {
                "updateTextStyle": {
                    "objectId": object_id,
                    "style": {
                        "bold": True,
                        "fontSize": {"magnitude": font_size + 2, "unit": "PT"},
                    },
                    "textRange": {
                        "type": "FIXED_RANGE",
                        "startIndex": bold_range[0],
                        "endIndex": bold_range[1],
                    },
                    "fields": "bold,fontSize",
                }
            }
        )
    return requests


def _dimension_to_pt(dimension: dict | None, default: float) -> float:
    if not dimension:
        return default
    magnitude = float(dimension.get("magnitude", default))
    unit = str(dimension.get("unit", "PT")).upper()
    if unit == "EMU":
        return magnitude / EMU_PER_PT
    return magnitude


def _new_object_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def _build_slides_service(credentials):
    from googleapiclient.discovery import build

    return build("slides", "v1", credentials=credentials)


def _get_google_credentials(config: GoogleSlidesConfig):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    client_secret_path = Path(config.oauth_client_secret_path)
    if not client_secret_path.exists():
        raise FileNotFoundError(
            f"Missing Google OAuth client secret file: {client_secret_path}"
        )

    token_path = Path(config.oauth_token_path)
    token_path.parent.mkdir(parents=True, exist_ok=True)

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(
            str(token_path),
            GOOGLE_SLIDES_SCOPES,
        )

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(client_secret_path),
            GOOGLE_SLIDES_SCOPES,
        )
        credentials = flow.run_local_server(
            host="localhost",
            port=0,
            open_browser=True,
            authorization_prompt_message=(
                "A browser window will open for Google Slides authorization.\n"
                "If it does not, copy this URL into Safari or Chrome:\n{url}\n"
            ),
            success_message="Google Slides authorization complete. You can close this window.",
        )
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return credentials
