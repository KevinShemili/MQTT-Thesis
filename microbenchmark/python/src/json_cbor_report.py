import matplotlib
import os

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from utils.statistics import GetStudentTCriticalValue95
from utils.statistics import Mean
from utils.statistics import MeanAndConfidenceInterval
from utils.parser import ParseIntListFromEnv

BENCH_FILE: str = "/results/json-cbor/bench_output.txt"
PNG_FILE: str = "/results/json-cbor/plot.png"
SIZE_PNG_FILE: str = "/results/json-cbor/size.png"
HTML_FILE: str = "/results/json-cbor/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/json_cbor_template.html"

RUNS: int = int(os.environ["JSON_CBOR_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)
ATTRIBUTE_COUNTS: list[int] = ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS")
FORMATS: list[str] = ["JSON", "CBOR", "CBORKeyAsInt"]
OPERATIONS: list[str] = ["serialize", "deserialize"]

JSON_COLOR: str = "#d97706"
CBOR_COLOR: str = "#7c3aed"
CBOR_KEYASINT_COLOR: str = "#0f766e"


class BenchmarkMetrics:

    def __init__(
        self,
        operation: str,
        formatName: str,
        attributeCount: int,
    ) -> None:

        self.Operation: str = operation
        self.Format: str = formatName
        self.AttributeCount: int = attributeCount

        self.Iterations: list[int] = []
        self.NsPerOperation: list[float] = []
        self.EnvelopeBytes: list[float] = []
        self.RawBytes: list[float] = []


def GetFormatColor(formatName: str) -> str:
    if formatName == "JSON":
        return JSON_COLOR

    if formatName == "CBOR":
        return CBOR_COLOR

    return CBOR_KEYASINT_COLOR


def GetFormatLabel(formatName: str) -> str:
    if formatName == "CBORKeyAsInt":
        return "CBOR (int keys)"

    return formatName


def ParseBenchmarkFile(filepath: str) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    prefix: str = "BenchmarkEnvelope"

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields: list[str] = line.strip().split()

            if len(fields) == 0:
                continue

            benchmarkName: str = fields[0]

            if not benchmarkName.startswith(prefix):
                continue

            # "Serialize/JSON/1Attrs" -> operation, format, attribute text.
            operation, formatName, attributeText, *_ = benchmarkName[
                len(prefix) :
            ].split("/")
            operation = operation.lower()

            # Strip GOMAXPROCS suffix (e.g. "-8") first, then the "Attrs" unit label.
            attributeCount: int = int(attributeText.split("-")[0].replace("Attrs", ""))

            benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    formatName,
                    attributeCount,
                )

            metrics: BenchmarkMetrics = results[benchmarkCaseId]

            iterationCount: int = int(fields[1])

            # Reads each "<value> <unit>" pair after ns/op. B/op and allocs/op may still be
            # present in this dict (Go still reports them), they are just not used below.
            metricsByUnit: dict[str, float] = {}
            for index in range(2, len(fields) - 1, 2):
                unitName: str = fields[index + 1]
                metricsByUnit[unitName] = float(fields[index])

            metrics.Iterations.append(iterationCount)
            metrics.NsPerOperation.append(metricsByUnit["ns/op"])
            metrics.EnvelopeBytes.append(metricsByUnit["envelope_bytes/op"])
            metrics.RawBytes.append(metricsByUnit["raw_bytes/op"])

    return results


def PlotLatency(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Latency vs. Policy Attributes",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for formatName in FORMATS:

            means: list[float] = []
            ciHalfs: list[float] = []
            counts: list[int] = []

            for attributeCount in ATTRIBUTE_COUNTS:

                benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                latencyMean, latencyCI = MeanAndConfidenceInterval(
                    metrics.NsPerOperation, T_95
                )

                counts.append(attributeCount)
                means.append(latencyMean / 1000.0)
                ciHalfs.append(latencyCI / 1000.0)

            axis.errorbar(
                counts,
                means,
                yerr=ciHalfs,
                label=GetFormatLabel(formatName),
                color=GetFormatColor(formatName),
                marker="o",
                linewidth=1.8,
                markersize=5,
                capsize=4,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Attribute count")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_yscale("log")
        axis.set_xticks(ATTRIBUTE_COUNTS)
        axis.grid(
            True,
            which="both",
            color="#ded9d2",
            linestyle="--",
            linewidth=0.5,
            alpha=0.7,
        )
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {PNG_FILE}")


def PlotSize(results: dict[str, BenchmarkMetrics]) -> None:

    # Two panels: absolute envelope size on the left, format tax (bytes added over raw) on the right.
    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "JSON vs. CBOR vs. CBOR (Int Keys): Envelope Size vs. Attribute Count",
        fontsize=13,
    )

    for formatName in FORMATS:

        sizes: list[float] = []
        overheadBytesList: list[float] = []
        counts: list[int] = []

        for attributeCount in ATTRIBUTE_COUNTS:

            benchmarkCaseId: str = f"serialize/{formatName}/{attributeCount}"
            metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
            if metrics is None:
                continue

            envelopeSize: float = Mean(metrics.EnvelopeBytes)
            rawSize: float = Mean(metrics.RawBytes)

            # Bytes added by the format over the raw payload — the fixed "tax" this format charges.
            overheadBytesValue: float = envelopeSize - rawSize

            counts.append(attributeCount)
            sizes.append(envelopeSize)
            overheadBytesList.append(overheadBytesValue)

        axes[0].plot(
            counts,
            sizes,
            label=GetFormatLabel(formatName),
            color=GetFormatColor(formatName),
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

        axes[1].plot(
            counts,
            overheadBytesList,
            label=GetFormatLabel(formatName),
            color=GetFormatColor(formatName),
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axes[0].set_title("Absolute Size", fontsize=11)
    axes[0].set_xlabel("Attribute count")
    axes[0].set_ylabel("Envelope size (bytes)")
    axes[0].set_xticks(ATTRIBUTE_COUNTS)
    axes[0].grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )
    axes[0].legend(fontsize=10)

    axes[1].set_title("Format Tax", fontsize=11)
    axes[1].set_xlabel("Attribute count")
    axes[1].set_ylabel("Bytes added over raw payload")
    axes[1].set_yscale("log")
    axes[1].set_xticks(ATTRIBUTE_COUNTS)
    axes[1].grid(
        True,
        which="both",
        color="#ded9d2",
        linestyle="--",
        linewidth=0.5,
        alpha=0.7,
    )
    axes[1].legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(SIZE_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {SIZE_PNG_FILE}")


def BuildOperationFormatTable(
    results: dict[str, BenchmarkMetrics],
    operation: str,
    formatName: str,
) -> str:

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Attributes</th>")
    lines.append("<th>Latency (ns/op)</th>")
    lines.append("<th>Raw (B)</th>")
    lines.append("<th>Envelope Size (B)</th>")
    lines.append("<th>Format Overhead (%)</th>")
    lines.append(f"<th>Iters (Σ{RUNS} runs)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for attributeCount in ATTRIBUTE_COUNTS:

        benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"
        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
        if metrics is None:
            continue

        latencyMean, latencyCI = MeanAndConfidenceInterval(metrics.NsPerOperation, T_95)

        envelopeSize: float = Mean(metrics.EnvelopeBytes)
        rawSize: float = Mean(metrics.RawBytes)

        overheadPercent: float = (envelopeSize - rawSize) / rawSize * 100.0

        caseIterations: int = 0

        for iterationCount in metrics.Iterations:
            caseIterations += iterationCount

        latencyText: str = f"{latencyMean:.2f} ± {latencyCI:.2f}"

        lines.append("<tr>")
        lines.append(f"<td>{attributeCount}</td>")
        lines.append(f"<td>{latencyText}</td>")
        lines.append(f"<td>{rawSize:.0f}</td>")
        lines.append(f"<td>{envelopeSize:.0f}</td>")
        lines.append(f"<td>{overheadPercent:.2f}%</td>")
        lines.append(f"<td>{caseIterations:,}</td>")
        lines.append("</tr>")

    lines.append("</tbody>")
    lines.append("</table>")

    return "\n".join(lines)


def WriteHtmlReport(results: dict[str, BenchmarkMetrics]) -> None:

    totalIterations: int = 0

    for metrics in results.values():
        for iterationCount in metrics.Iterations:
            totalIterations += iterationCount

    # Six filtered tables — one per operation/format pair.
    serializeJsonTable: str = BuildOperationFormatTable(results, "serialize", "JSON")
    serializeCborTable: str = BuildOperationFormatTable(results, "serialize", "CBOR")
    serializeCborKeyAsIntTable: str = BuildOperationFormatTable(
        results, "serialize", "CBORKeyAsInt"
    )
    deserializeJsonTable: str = BuildOperationFormatTable(
        results, "deserialize", "JSON"
    )
    deserializeCborTable: str = BuildOperationFormatTable(
        results, "deserialize", "CBOR"
    )
    deserializeCborKeyAsIntTable: str = BuildOperationFormatTable(
        results, "deserialize", "CBORKeyAsInt"
    )

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")
    report = report.replace("{{SerializeJsonTable}}", serializeJsonTable)
    report = report.replace("{{SerializeCborTable}}", serializeCborTable)
    report = report.replace(
        "{{SerializeCborKeyAsIntTable}}", serializeCborKeyAsIntTable
    )
    report = report.replace("{{DeserializeJsonTable}}", deserializeJsonTable)
    report = report.replace("{{DeserializeCborTable}}", deserializeCborTable)
    report = report.replace(
        "{{DeserializeCborKeyAsIntTable}}", deserializeCborKeyAsIntTable
    )
    report = report.replace("{{LatencyPlot}}", "plot.png")
    report = report.replace("{{SizePlot}}", "size.png")

    with open(HTML_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {HTML_FILE}")


def Main() -> None:

    try:
        results: dict[str, BenchmarkMetrics] = ParseBenchmarkFile(BENCH_FILE)
    except FileNotFoundError:
        sys.exit(f"[error] {BENCH_FILE} not found — run the benchmark first")

    PlotLatency(results)
    PlotSize(results)
    WriteHtmlReport(results)


if __name__ == "__main__":
    Main()
