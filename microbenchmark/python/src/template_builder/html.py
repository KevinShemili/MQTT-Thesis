from typing import Sequence

from statistics_tbd.summary import get_student_t_critical_95

CONFIDENCE_LEVEL = "95%"

# A row is marked where the Raspberry Pi firmware throttled the clock while that case was
# being measured, which makes the measurement a pessimistic bound rather than an invalid
# one. The column is drawn only where something actually throttled, since a column of
# identical marks repeated across every table would bury the rows that matter
THERMAL_MARK = "&#9888;"

# A row the rest of the report is quoted against, ex. the fixed RSA key size the
# cross-schema comparisons use, is marked so it can be found among the swept values
REFERENCE_ROW_CLASS = "reference-row"
THERMAL_FLAGGED_NOTE = (
    "&#9888; marks a case measured while the Raspberry Pi firmware was thermally "
    "throttling. Those measurements are a pessimistic bound, not an invalid one."
)
THERMAL_CLEAN_NOTE = "No thermal throttling occurred while these cases were measured."

OUT_OF_MEMORY_NOTICE_HEADERS = ["OPERATION", "CASE", "RESULT"]
OUT_OF_MEMORY_NOTICE_NOTE = (
    "These timing or key-generation cases ran out of memory. Any partial measurements "
    "they emitted are excluded from the figures and tables below."
)


# Builds HTML table, given header names and row values. The throttle flags are positional,
# one per row, and are left out entirely for a benchmark that carries no throttle readings.
# The highlight flags are positional in the same way
def build_html_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    throttled: list[bool] | None = None,
    thermal_header: str = "Thermal",
    highlighted: list[bool] | None = None,
) -> str:

    flagged = throttled is not None and any(throttled)

    lines = ["<table>", "<thead>", "<tr>"]
    lines += [f"<th>{header}</th>" for header in headers]

    if flagged:
        lines.append(f"<th>{thermal_header}</th>")

    lines += ["</tr>", "</thead>", "<tbody>"]

    for index, row in enumerate(rows):

        if highlighted is not None and highlighted[index]:
            lines.append(f'<tr class="{REFERENCE_ROW_CLASS}">')
        else:
            lines.append("<tr>")

        lines += [f"<td>{cell}</td>" for cell in row]

        if flagged:
            mark = THERMAL_MARK if throttled[index] else ""  # type: ignore
            lines.append(f'<td class="thermal">{mark}</td>')

        lines.append("</tr>")

    lines += ["</tbody>", "</table>"]

    # The note explains the mark where there is one, and confirms the absence of
    # throttling where the column has been left out
    if throttled is not None:
        note = THERMAL_FLAGGED_NOTE if flagged else THERMAL_CLEAN_NOTE
        lines.append(f'<p class="table-note">{note}</p>')

    return "\n".join(lines)


# A run in which every process finished has nothing to report here, so the whole section
# collapses to an empty string and leaves no trace in the page
def build_html_out_of_memory_notice(rows: Sequence[Sequence[str]]) -> str:

    if not rows:
        return ""

    return "\n".join(
        [
            '<section class="section failure-notice">',
            '<div class="section-heading">',
            "<h2>Out of Memory</h2>",
            f"<p>{OUT_OF_MEMORY_NOTICE_NOTE}</p>",
            "</div>",
            '<div class="table-block">',
            '<div class="table-wrapper">',
            build_html_table(OUT_OF_MEMORY_NOTICE_HEADERS, rows),
            "</div>",
            "</div>",
            "</section>",
        ]
    )


# Report values shared by all scenarios:
# 1. runs
# 2. t_critical
# 3. iteration_total
def build_html_generic_data(
    runs: int,
    iteration_total: int,
) -> dict[str, str]:

    return {
        "RunCount": str(runs),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        "TMultiplier": str(get_student_t_critical_95(runs - 1)),
        "TotalIterations": f"{iteration_total:,}",
    }


# Builds final HTML report by replacing template placeholders with actual values
def build_html_report(
    template_path: str,
    output_path: str,
    placeholders: dict[str, str],
) -> None:

    with open(template_path, "r", encoding="utf-8") as file:
        report = file.read()

    for name, value in placeholders.items():
        report = report.replace(f"{{{{{name}}}}}", value)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {output_path}")
