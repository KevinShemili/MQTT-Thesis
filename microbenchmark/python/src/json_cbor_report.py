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
MEMORY_PNG_FILE: str = "/results/json-cbor/memory.png"
OVERHEAD_PNG_FILE: str = "/results/json-cbor/overhead.png"
ALLOCS_PNG_FILE: str = "/results/json-cbor/allocs.png"
HTML_FILE: str = "/results/json-cbor/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/json_cbor_template.html"

RUNS: int = int(os.environ["JSON_CBOR_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)
ATTRIBUTE_COUNTS: list[int] = ParseIntListFromEnv("JSON_CBOR_ATTRIBUTE_COUNTS")
FORMATS: list[str] = ["JSON", "CBOR"]
OPERATIONS: list[str] = ["serialize", "deserialize"]

JSON_COLOR: str = "#be0c24"
CBOR_COLOR: str = "#300bb6"


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
        self.BytesPerOperation: list[float] = []
        self.AllocsPerOperation: list[float] = []


def GetFormatColor(formatName: str) -> str:
    if formatName == "JSON":
        return JSON_COLOR

    return CBOR_COLOR


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

            # Reads each "<value> <unit>" pair after ns/op, regardless of which metrics are present.
            metricsByUnit: dict[str, float] = {}
            for index in range(2, len(fields) - 1, 2):
                unitName: str = fields[index + 1]
                metricsByUnit[unitName] = float(fields[index])

            metrics.Iterations.append(iterationCount)
            metrics.NsPerOperation.append(metricsByUnit["ns/op"])
            metrics.EnvelopeBytes.append(metricsByUnit["envelope_bytes/op"])
            metrics.RawBytes.append(metricsByUnit["raw_bytes/op"])
            metrics.BytesPerOperation.append(metricsByUnit["B/op"])
            metrics.AllocsPerOperation.append(metricsByUnit["allocs/op"])

    return results


def PlotLatency(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "JSON vs CBOR (Latency vs Attribute Count)",
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
                label=formatName,
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
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {PNG_FILE}")


def PlotSize(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axis = plt.subplots(figsize=(8, 5))

    figure.suptitle(
        "JSON vs CBOR (Envelope Size vs Attribute Count)",
        fontsize=13,
    )

    for formatName in FORMATS:

        sizes: list[float] = []
        counts: list[int] = []

        for attributeCount in ATTRIBUTE_COUNTS:

            benchmarkCaseId: str = f"serialize/{formatName}/{attributeCount}"
            metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
            if metrics is None:
                continue

            sizeMean: float = Mean(metrics.EnvelopeBytes)

            counts.append(attributeCount)
            sizes.append(sizeMean)

        axis.plot(
            counts,
            sizes,
            label=formatName,
            color=GetFormatColor(formatName),
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axis.set_xlabel("Attribute count")
    axis.set_ylabel("Envelope size (bytes)")
    axis.set_xticks(ATTRIBUTE_COUNTS)
    axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
    axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(SIZE_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {SIZE_PNG_FILE}")


def PlotMemory(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "JSON vs CBOR (Memory vs Attribute Count)",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for formatName in FORMATS:

            counts: list[int] = []
            bytesPerOp: list[float] = []

            for attributeCount in ATTRIBUTE_COUNTS:

                benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                memoryMean: float = Mean(metrics.BytesPerOperation)

                counts.append(attributeCount)
                bytesPerOp.append(memoryMean)

            axis.plot(
                counts,
                bytesPerOp,
                label=formatName,
                color=GetFormatColor(formatName),
                marker="o",
                linewidth=1.8,
                markersize=5,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Attribute count")
        axis.set_ylabel("Memory (B/op)")
        axis.set_xticks(ATTRIBUTE_COUNTS)
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(MEMORY_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {MEMORY_PNG_FILE}")


def PlotFormatOverhead(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axis = plt.subplots(figsize=(8, 5))

    figure.suptitle(
        "JSON vs CBOR (Format Overhead vs Attribute Count)",
        fontsize=13,
    )

    for formatName in FORMATS:

        percentages: list[float] = []
        counts: list[int] = []

        for attributeCount in ATTRIBUTE_COUNTS:

            benchmarkCaseId: str = f"serialize/{formatName}/{attributeCount}"
            metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
            if metrics is None:
                continue

            envelopeSize: float = Mean(metrics.EnvelopeBytes)
            rawSize: float = Mean(metrics.RawBytes)

            # Percentage growth from raw to envelope — X% such that raw + X% of raw = envelope.
            overheadPercent: float = (envelopeSize - rawSize) / rawSize * 100.0

            counts.append(attributeCount)
            percentages.append(overheadPercent)

        axis.plot(
            counts,
            percentages,
            label=formatName,
            color=GetFormatColor(formatName),
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axis.set_xlabel("Attribute count")
    axis.set_ylabel("Format overhead (% growth over raw)")
    axis.set_xticks(ATTRIBUTE_COUNTS)
    axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
    axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(OVERHEAD_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {OVERHEAD_PNG_FILE}")


def PlotAllocs(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "JSON vs CBOR (Allocations vs Attribute Count)",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for formatName in FORMATS:

            counts: list[int] = []
            allocs: list[float] = []

            for attributeCount in ATTRIBUTE_COUNTS:

                benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                allocsMean: float = Mean(metrics.AllocsPerOperation)

                counts.append(attributeCount)
                allocs.append(allocsMean)

            axis.plot(
                counts,
                allocs,
                label=formatName,
                color=GetFormatColor(formatName),
                marker="o",
                linewidth=1.8,
                markersize=5,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Attribute count")
        axis.set_ylabel("Allocations (allocs/op)")
        axis.set_xticks(ATTRIBUTE_COUNTS)
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(ALLOCS_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {ALLOCS_PNG_FILE}")


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
    lines.append("<th>Memory (B/op)</th>")
    lines.append("<th>Allocs/op</th>")
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

        bytesPerOp: float = Mean(metrics.BytesPerOperation)
        allocsPerOp: float = Mean(metrics.AllocsPerOperation)

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
        lines.append(f"<td>{bytesPerOp:.0f}</td>")
        lines.append(f"<td>{allocsPerOp:.1f}</td>")
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

    # Four filtered tables instead of one crowded table — one per operation/format pair.
    serializeJsonTable: str = BuildOperationFormatTable(results, "serialize", "JSON")
    serializeCborTable: str = BuildOperationFormatTable(results, "serialize", "CBOR")
    deserializeJsonTable: str = BuildOperationFormatTable(
        results, "deserialize", "JSON"
    )
    deserializeCborTable: str = BuildOperationFormatTable(
        results, "deserialize", "CBOR"
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
    report = report.replace("{{DeserializeJsonTable}}", deserializeJsonTable)
    report = report.replace("{{DeserializeCborTable}}", deserializeCborTable)
    report = report.replace("{{LatencyPlot}}", "plot.png")
    report = report.replace("{{SizePlot}}", "size.png")
    report = report.replace("{{MemoryPlot}}", "memory.png")
    report = report.replace("{{OverheadPlot}}", "overhead.png")
    report = report.replace("{{AllocsPlot}}", "allocs.png")

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
    PlotMemory(results)
    PlotFormatOverhead(results)
    PlotAllocs(results)
    WriteHtmlReport(results)


if __name__ == "__main__":
    Main()
