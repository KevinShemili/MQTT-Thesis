from typing import Iterable, Sequence

CONFIDENCE_LEVEL = "95%"


def render_table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> str:

    lines = ["<table>", "<thead>", "<tr>"]
    lines += [f"<th>{header}</th>" for header in headers]
    lines += ["</tr>", "</thead>", "<tbody>"]

    for row in rows:
        lines.append("<tr>")
        lines += [f"<td>{cell}</td>" for cell in row]
        lines.append("</tr>")

    lines += ["</tbody>", "</table>"]

    return "\n".join(lines)


def common_placeholders(
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


def render_report(
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
