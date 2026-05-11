from __future__ import annotations

from datetime import datetime
from html import escape

from .booking_text import clean_booking_for_display
from .condense import build_condensed_summary
from .model import CondensedScheduleSummary, ScheduleSummary


def render_summary_table_fragment(
    summary: CondensedScheduleSummary,
    include_styles: bool = False,
) -> str:
    header_cols = "".join(f"<th>{escape(space)}</th>" for space in summary.spaces)
    body_cells = []
    for space in summary.spaces:
        entries = summary.by_space.get(space, [])
        if not entries:
            body_cells.append("<td class='open'><div class='free'>Free all day</div></td>")
            continue

        parts = []
        for entry in entries:
            parts.append(
                "<div class='entry'>"
                f"<div class='who'>{escape(clean_booking_for_display(entry.booking))}</div>"
                f"<div class='when'>{escape(entry.when)}</div>"
                "</div>"
            )
        body_cells.append(f"<td class='booked'>{''.join(parts)}</td>")

    table_html = (
        "<table class='summary-table'>"
        "<thead><tr>"
        f"{header_cols}"
        "</tr></thead>"
        "<tbody><tr>"
        f"{''.join(body_cells)}"
        "</tr></tbody>"
        "</table>"
    )
    if not include_styles:
        return table_html
    return _summary_table_styles() + table_html


def render_html_report(summary: ScheduleSummary) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    date_label = summary.report_date.strftime("%A, %B %-d, %Y")
    condensed = build_condensed_summary(summary)
    summary_table = render_summary_table_fragment(condensed)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Library Spaces Daily Schedule</title>
  <style>
    :root {{
      --ink: #132a3f;
      --accent: #005b96;
      --grid: #cfd8e3;
      --booked-bg: #eaf2fb;
      --open-bg: #f7fafc;
    }}
    body {{
      margin: 24px;
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      color: var(--ink);
      background: linear-gradient(180deg, #fbfdff 0%, #f2f6fa 100%);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      letter-spacing: 0.02em;
    }}
    .meta {{
      margin-bottom: 14px;
      font-size: 14px;
      color: #35526f;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
      background: white;
    }}
    th, td {{
      border: 1px solid var(--grid);
      padding: 8px 10px;
      vertical-align: top;
      font-size: 13px;
      line-height: 1.25;
      word-wrap: break-word;
    }}
    th {{
      background: var(--accent);
      color: white;
      font-weight: 600;
      text-align: left;
    }}
    td.period {{
      font-weight: 700;
      background: #eef4fa;
      width: 110px;
    }}
    td.booked {{
      background: var(--booked-bg);
    }}
    td.open {{
      background: var(--open-bg);
      color: #6b7f92;
    }}
    table.summary-table td {{
      min-height: 120px;
    }}
    .entry {{
      margin-bottom: 10px;
      padding-bottom: 10px;
      border-bottom: 1px solid rgba(19, 42, 63, 0.12);
    }}
    .entry:last-child {{
      margin-bottom: 0;
      padding-bottom: 0;
      border-bottom: 0;
    }}
    .who {{
      font-weight: 700;
      margin-bottom: 4px;
    }}
    .when {{
      color: #35526f;
      font-size: 12px;
    }}
    .free {{
      font-weight: 600;
      min-height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    @media print {{
      body {{
        margin: 0;
        background: white;
      }}
      .noprint {{
        display: none;
      }}
      th, td {{
        font-size: 11px;
      }}
    }}
  </style>
</head>
<body>
  <h1>Library Spaces Daily Schedule</h1>
  <div class="meta"><strong>{escape(date_label)}</strong> | Generated {escape(generated_at)}</div>
  <button class="noprint" onclick="window.print()">Print</button>
  {summary_table}
</body>
</html>
"""


def _summary_table_styles() -> str:
    return """
<style>
  table.summary-table {
    width: 100%;
    border-collapse: collapse;
    table-layout: fixed;
    background: white;
    margin-bottom: 12px;
  }
  .summary-table th,
  .summary-table td {
    border: 1px solid #cfd8e3;
    padding: 10px 12px;
    vertical-align: top;
    font-size: 13px;
    line-height: 1.3;
    word-wrap: break-word;
  }
  .summary-table th {
    background: #005b96;
    color: white;
    font-weight: 600;
    text-align: left;
  }
  .summary-table td.booked {
    background: #eaf2fb;
  }
  .summary-table td.open {
    background: #f7fafc;
    color: #6b7f92;
  }
  .summary-table .entry {
    margin-bottom: 10px;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(19, 42, 63, 0.12);
  }
  .summary-table .entry:last-child {
    margin-bottom: 0;
    padding-bottom: 0;
    border-bottom: 0;
  }
  .summary-table .who {
    font-weight: 700;
    margin-bottom: 4px;
  }
  .summary-table .when {
    color: #35526f;
    font-size: 12px;
  }
  .summary-table .free {
    font-weight: 600;
    min-height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
"""
