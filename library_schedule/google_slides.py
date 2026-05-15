from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from uuid import uuid4

from .booking_text import clean_booking_for_display
from .config import GoogleSlidesConfig
from .model import CalendarAgenda, CondensedScheduleSummary, SummaryEntry


GOOGLE_SLIDES_SCOPES = ["https://www.googleapis.com/auth/presentations"]
EMU_PER_PT = 12700
SLIDE_EVENT_LIMIT = 3


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
        left=140,
        top=34,
        width=520,
        height=30,
        text=_build_title_text(summary),
        font_size=24,
        bold_range=(0, len(_build_title_text(summary))),
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
        if event.when:
            parts.append(event.when)
        if event.details:
            parts.append(event.details)
        parts.append("")
    remaining = len(agenda.events) - max_events
    if remaining > 0:
        parts.append(f"+{remaining} more")
    return "\n".join(parts).rstrip()


def _build_title_text(summary: CondensedScheduleSummary) -> str:
    return summary.report_date.strftime("%A, %B %-d, %Y")


def _build_room_card_requests(
    slide_id: str,
    summary: CondensedScheduleSummary,
    page_width_pt: float,
    page_height_pt: float,
    calendar_agenda: CalendarAgenda | None = None,
) -> list[dict]:
    gutter = 10
    top = 86
    table_width = min(800.0, page_width_pt - 84)
    left = (page_width_pt - table_width) / 2
    bottom_margin = 62
    content_height = page_height_pt - top - bottom_margin
    content_width = table_width
    requests: list[dict] = []

    if calendar_agenda is None:
        requests.extend(
            _build_card_grid_requests(
                slide_id=slide_id,
                cards=[
                    (
                        room_name,
                        format_room_card_text(room_name, summary.by_space.get(room_name, [])),
                    )
                    for room_name in summary.spaces
                ],
                left=left,
                top=top,
                width=content_width,
                height=content_height,
                columns=4,
                gutter=gutter,
                font_size=12,
                object_prefix="room",
            )
        )
        return requests

    calendar_height = 132.0
    room_height = content_height - calendar_height - gutter
    requests.extend(
        _build_card_grid_requests(
            slide_id=slide_id,
            cards=[
                (
                    room_name,
                    format_room_card_text(room_name, summary.by_space.get(room_name, [])),
                )
                for room_name in summary.spaces
            ],
            left=left,
            top=top,
            width=content_width,
            height=room_height,
            columns=4,
            gutter=gutter,
            font_size=12,
            object_prefix="room",
        )
    )
    requests.extend(
        _textbox_request(
            page_id=slide_id,
            object_id=_new_object_id("calendar"),
            left=left,
            top=top + room_height + gutter,
            width=content_width,
            height=calendar_height,
            text=format_calendar_card_text(calendar_agenda),
            font_size=11,
            bold_range=(0, len(f"{calendar_agenda.source_name} Events")),
        )
    )
    return requests


def _build_card_grid_requests(
    slide_id: str,
    cards: list[tuple[str, str]],
    left: float,
    top: float,
    width: float,
    height: float,
    columns: int,
    gutter: float,
    font_size: int,
    object_prefix: str,
) -> list[dict]:
    rows = max(1, (len(cards) + columns - 1) // columns)
    card_width = (width - (gutter * (columns - 1))) / columns
    card_height = (height - (gutter * max(rows - 1, 0))) / rows

    requests: list[dict] = []
    for index, (card_title, card_text) in enumerate(cards):
        col = index % columns
        row = index // columns
        requests.extend(
            _textbox_request(
                page_id=slide_id,
                object_id=_new_object_id(f"{object_prefix}_{index + 1}"),
                left=left + col * (card_width + gutter),
                top=top + row * (card_height + gutter),
                width=card_width,
                height=card_height,
                text=card_text,
                font_size=font_size,
                bold_range=(0, len(card_title)),
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
