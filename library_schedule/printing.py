from __future__ import annotations

from pathlib import Path
import subprocess


def render_html_report_to_pdf(
    html_path: str | Path,
    pdf_path: str | Path,
) -> Path:
    from playwright.sync_api import sync_playwright

    html_file = Path(html_path).resolve()
    pdf_file = Path(pdf_path).resolve()
    pdf_file.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html_file.as_uri(), wait_until="load")
        page.emulate_media(media="print")
        page.pdf(
            path=str(pdf_file),
            format="Letter",
            print_background=True,
            margin={
                "top": "0.35in",
                "right": "0.35in",
                "bottom": "0.35in",
                "left": "0.35in",
            },
        )
        browser.close()

    return pdf_file


def print_file(
    file_path: str | Path,
    printer_name: str | None = None,
) -> str:
    command = build_print_command(file_path, printer_name)
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return (result.stdout or result.stderr).strip()


def build_print_command(
    file_path: str | Path,
    printer_name: str | None = None,
) -> list[str]:
    command = ["lp"]
    if printer_name:
        command.extend(["-d", printer_name])
    command.append(str(Path(file_path)))
    return command
