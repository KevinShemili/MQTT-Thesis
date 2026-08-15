from typing import Sequence

CONFIDENCE_LEVEL = "95%"

# A row is marked where the Raspberry Pi firmware throttled the clock while that case was
# being measured, which makes the measurement a pessimistic bound rather than an invalid
# one. The column is drawn only where something actually throttled, since a column of
# identical marks repeated across every table would bury the rows that matter
THERMAL_MARK = "&#9888;"
THERMAL_FLAGGED_NOTE = (
    "&#9888; marks a case measured while the Raspberry Pi firmware was thermally "
    "throttling. Those measurements are a pessimistic bound, not an invalid one."
)
THERMAL_CLEAN_NOTE = "No thermal throttling occurred while these cases were measured."

FAILURE_NOTICE_HEADERS = ["OPERATION", "CASE", "SAMPLE", "EXIT CODE", "DIAGNOSIS"]
FAILURE_NOTICE_NOTE = (
    "Everything these processes printed before they stopped is kept in "
    "<code>case_logs/</code>. The cases they belong to are left out of every figure and "
    "table below rather than being averaged from partial output."
)


# Builds HTML table, given header names and row values. The throttle flags are positional,
# one per row, and are left out entirely for a benchmark that carries no throttle readings
def build_html_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    throttled: list[bool] | None = None,
    thermal_header: str = "Thermal",
) -> str:

    flagged = throttled is not None and any(throttled)

    lines = ["<table>", "<thead>", "<tr>"]
    lines += [f"<th>{header}</th>" for header in headers]

    if flagged:
        lines.append(f"<th>{thermal_header}</th>")

    lines += ["</tr>", "</thead>", "<tbody>"]

    for index, row in enumerate(rows):
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
def build_html_failure_notice(rows: Sequence[Sequence[str]]) -> str:

    if not rows:
        return ""

    return "\n".join(
        [
            '<section class="section failure-notice">',
            '<div class="section-heading">',
            "<h2>Incomplete Cases</h2>",
            f"<p>{FAILURE_NOTICE_NOTE}</p>",
            "</div>",
            '<div class="table-block">',
            '<div class="table-wrapper">',
            build_html_table(FAILURE_NOTICE_HEADERS, rows),
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
    t_critical: float,
    iteration_total: int,
) -> dict[str, str]:

    return {
        "RunCount": str(runs),
        "ConfidenceLevel": CONFIDENCE_LEVEL,
        "TMultiplier": str(t_critical),
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
