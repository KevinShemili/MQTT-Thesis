import re
import math
import matplotlib

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt

BENCH_FILE: str = "/results/json-cbor/bench_output.txt"
PNG_FILE: str = "/results/json-cbor/plot.png"
SIZE_PNG_FILE: str = "/results/json-cbor/size.png"
MEMORY_PNG_FILE: str = "/results/json-cbor/memory.png"
OVERHEAD_PNG_FILE: str = "/results/json-cbor/overhead.png"
ALLOCS_PNG_FILE: str = "/results/json-cbor/allocs.png"
HTML_FILE: str = "/results/json-cbor/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/json_cbor_template.html"

RUNS: int = 4
T_95_D3: float = 3.182

ATTRIBUTE_COUNTS: list[int] = [1, 2, 5, 10, 20, 50]
FORMATS: list[str] = ["JSON", "CBOR"]
OPERATIONS: list[str] = ["serialize", "deserialize"]

JSON_COLOR: str = "#be0c24"
CBOR_COLOR: str = "#300bb6"

# Order after ns/op follows Go's alphabetical sort of custom metrics: envelope_bytes/op, raw_bytes/op, then B/op, allocs/op.
LINE_PATTERN = re.compile(
    r"^BenchmarkEnvelope(Serialize|Deserialize)/([^/]+)/(\d+)Attrs(?:-\d+)?\s+"
    r"(\d+)\s+"
    r"([\d.]+)\s+ns/op"
    r"(?:\s+([\d.]+)\s+envelope_bytes/op)?"
    r"(?:\s+([\d.]+)\s+raw_bytes/op)?"
    r"(?:\s+([\d.]+)\s+B/op)?"
    r"(?:\s+([\d.]+)\s+allocs/op)?"
    r"$"
)


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
        # Raw field size before serialization, used to isolate format overhead.
        self.RawBytes: list[float] = []
        self.BytesPerOperation: list[float] = []
        # Allocation count per op, from -test.benchmem.
        self.AllocsPerOperation: list[float] = []


def GetFormatColor(formatName: str) -> str:
    if formatName == "JSON":
        return JSON_COLOR

    return CBOR_COLOR


def ParseBenchmarkFile(filepath: str) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:

            match = LINE_PATTERN.match(line.strip())
            if match is None:
                continue

            operation: str = match.group(1).lower()
            formatName: str = match.group(2)
            attributeCount: int = int(match.group(3))

            benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    formatName,
                    attributeCount,
                )

            metrics: BenchmarkMetrics = results[benchmarkCaseId]

            metrics.Iterations.append(int(match.group(4)))
            metrics.NsPerOperation.append(float(match.group(5)))
            metrics.EnvelopeBytes.append(float(match.group(6)))
            metrics.RawBytes.append(float(match.group(7)))
            metrics.BytesPerOperation.append(float(match.group(8)))
            metrics.AllocsPerOperation.append(float(match.group(9)))

    return results


def Mean(values: list[float] | list[int]) -> float:
    # Average repeated samples for one exact benchmark case.
    return sum(values) / len(values)


def MeanAndCI(values: list[float]) -> tuple[float, float]:
    valueCount: int = len(values)

    # Mean latency across RUNS independent executions of the same benchmark case.
    mean: float = Mean(values)

    # Accumulate how far each run is from the mean.
    squaredDeviationSum: float = 0.0

    for value in values:
        squaredDeviationSum += (value - mean) ** 2

    # Use n - 1 because these RUNS are a sample of possible benchmark runs.
    variance: float = squaredDeviationSum / (valueCount - 1)

    # Standard deviation describes run-to-run spread in ns/op.
    standardDeviation: float = math.sqrt(variance)

    # Standard error describes uncertainty of the mean, not individual run spread.
    standardError: float = standardDeviation / math.sqrt(valueCount)

    # 95% CI half-width around the mean using Student's t for df = RUNS - 1.
    ciHalf: float = T_95_D3 * standardError

    return mean, ciHalf


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

                latencyMean, latencyCI = MeanAndCI(metrics.NsPerOperation)

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

            # Overhead is the extra bytes the format adds beyond the raw fields, as a percentage of the raw size.
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
    axis.set_ylabel("Format overhead (% of raw fields)")
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


def BuildHtmlTable(results: dict[str, BenchmarkMetrics]) -> str:

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Op</th>")
    lines.append("<th>Format</th>")
    lines.append("<th>Attributes</th>")
    lines.append("<th>Latency (ns/op)</th>")
    lines.append("<th>Raw (B)</th>")
    lines.append("<th>Envelope Size (B)</th>")
    lines.append("<th>Format Overhead (%)</th>")
    lines.append("<th>Memory (B/op)</th>")
    lines.append("<th>Allocs/op</th>")
    lines.append("<th>Iters (Σ4 runs)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for operation in OPERATIONS:

        for formatName in FORMATS:

            for attributeCount in ATTRIBUTE_COUNTS:

                benchmarkCaseId: str = f"{operation}/{formatName}/{attributeCount}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                latencyMean, latencyCI = MeanAndCI(metrics.NsPerOperation)

                envelopeSize: float = Mean(metrics.EnvelopeBytes)

                rawSize: float = Mean(metrics.RawBytes)

                # Overhead is computed the same way on every row since raw and envelope size are both reported unconditionally.
                overheadPercent: float = (envelopeSize - rawSize) / rawSize * 100.0

                bytesPerOp: float = Mean(metrics.BytesPerOperation)

                allocsPerOp: float = Mean(metrics.AllocsPerOperation)

                caseIterations: int = 0

                for iterationCount in metrics.Iterations:
                    caseIterations += iterationCount

                latencyText: str = f"{latencyMean:.2f} ± {latencyCI:.2f}"

                lines.append("<tr>")
                lines.append(f"<td>{operation}</td>")
                lines.append(f"<td>{formatName}</td>")
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

    htmlTable: str = BuildHtmlTable(results)

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95_D3))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")
    report = report.replace("{{SummaryTable}}", htmlTable)
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
