from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from .model import FetchedSchedulePage


def save_fetch_debug_artifacts(
    pages: list[FetchedSchedulePage],
    output_root: str | Path = "output/debug",
) -> Path:
    root = Path(output_root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = root / stamp
    session_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict[str, str | int | None]] = []
    for index, page in enumerate(pages, start=1):
        room_slug = _slugify(page.room_name or f"page_{index}")
        file_name = f"{index:02d}_{room_slug}.html"
        file_path = session_dir / file_name
        file_path.write_text(page.html, encoding="utf-8")
        manifest.append(
            {
                "index": index,
                "room_name": page.room_name,
                "final_url": page.final_url,
                "html_file": file_name,
            }
        )

    (session_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )

    latest_marker = root / "LATEST.txt"
    latest_marker.parent.mkdir(parents=True, exist_ok=True)
    latest_marker.write_text(str(session_dir), encoding="utf-8")
    return session_dir


def _slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    return normalized or "page"
