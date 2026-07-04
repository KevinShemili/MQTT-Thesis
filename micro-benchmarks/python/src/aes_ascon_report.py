import re
import math
import matplotlib

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BENCH_FILE: str = "/results/aes-ascon/bench_output.txt"
PNG_FILE: str = "/results/aes-ascon/plot.png"
THROUGHPUT_PNG_FILE: str = "/results/aes-ascon/throughput.png"
OVERHEAD_PNG_FILE: str = "/results/aes-ascon/overhead.png"
HTML_FILE: str = "/results/aes-ascon/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/aes_ascon_template.html"

RUNS: int = 4
T_95_D7: float = 3.182

PAYLOAD_SIZES: list[int] = [16, 64, 256, 1024, 4096, 16384, 65536]
ALGORITHMS: list[str] = ["AES-GCM", "ASCON"]
OPERATIONS: list[str] = ["encrypt", "decrypt"]

AES_GCM_COLOR: str = "#be0c24"
ASCON_COLOR: str = "#300bb6"

LINE_PATTERN = re.compile(
    r"^BenchmarkAESASCON(Encrypt|Decrypt)/([^/]+)/(\d+)B(?:-\d+)?\s+"
    r"(\d+)\s+"
    r"([\d.]+)\s+ns/op"
    r"(?:\s+([\d.]+)\s+MB/s)?"
    r"(?:\s+([\d.]+)\s+overhead_bytes/op)?"
    r"(?:\s+\d+\s+B/op)?"
    r"(?:\s+\d+\s+allocs/op)?"
    r"$"
)


class BenchmarkMetrics:

    def __init__(
        self,
        operation: str,
        algorithm: str,
        payloadSize: int,
    ) -> None:

        self.Operation: str = operation
        self.Algorithm: str = algorithm
        self.PayloadSize: int = payloadSize

        self.Iterations: list[int] = []
        self.NsPerOperation: list[float] = []
        self.MbPerSecond: list[float] = []
        self.OverheadBytes: list[float] = []


def GetAlgorithmColor(algorithm: str) -> str:
    if algorithm == "AES-GCM":
        return AES_GCM_COLOR

    return ASCON_COLOR


def FormatBytes(value: int) -> str:
    if value >= 1024:
        return f"{value // 1024}KB"

    return f"{value}B"


def ParseBenchmarkFile(filepath: str) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    with open(filepath, "r", encoding="utf-8") as file:
        for line in file:

            match = LINE_PATTERN.match(line.strip())
            if match is None:
                continue

            operation: str = match.group(1).lower()
            algorithm: str = match.group(2)
            payloadSize: int = int(match.group(3))

            benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    algorithm,
                    payloadSize,
                )

            metrics: BenchmarkMetrics = results[benchmarkCaseId]

            metrics.Iterations.append(int(match.group(4)))
            metrics.NsPerOperation.append(float(match.group(5)))
            metrics.MbPerSecond.append(float(match.group(6)))
            metrics.OverheadBytes.append(float(match.group(7)))

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
    ciHalf: float = T_95_D7 * standardError

    return mean, ciHalf


def PlotLatency(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "AES-GCM vs ASCON (Latency vs Payload Size)",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for algorithm in ALGORITHMS:

            means: list[float] = []
            ciHalfs: list[float] = []
            sizes: list[int] = []

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                latencyMean, latencyCI = MeanAndCI(metrics.NsPerOperation)

                sizes.append(payloadSize)
                means.append(latencyMean / 1000.0)
                ciHalfs.append(latencyCI / 1000.0)

            axis.errorbar(
                sizes,
                means,
                yerr=ciHalfs,
                label=algorithm,
                color=GetAlgorithmColor(algorithm),
                marker="o",
                linewidth=1.8,
                markersize=5,
                capsize=4,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Latency (µs) ± 95% CI")
        axis.set_xscale("log", base=2)
        axis.set_yscale("log")
        axis.set_xticks(PAYLOAD_SIZES)
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _: FormatBytes(int(value)))
        )
        axis.tick_params(axis="x", rotation=30)
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {PNG_FILE}")


def PlotThroughput(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "AES-GCM vs ASCON (Throughput vs Payload Size)",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for algorithm in ALGORITHMS:

            means: list[float] = []
            sizes: list[int] = []

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                throughputMean: float = Mean(metrics.MbPerSecond)

                sizes.append(payloadSize)
                means.append(throughputMean)

            axis.plot(
                sizes,
                means,
                label=algorithm,
                color=GetAlgorithmColor(algorithm),
                marker="o",
                linewidth=1.8,
                markersize=5,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Throughput (MB/s)")
        axis.set_xscale("log", base=2)
        axis.set_yscale("log")
        axis.set_xticks(PAYLOAD_SIZES)
        axis.xaxis.set_major_formatter(
            FuncFormatter(lambda value, _: FormatBytes(int(value)))
        )
        axis.tick_params(axis="x", rotation=30)
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(THROUGHPUT_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {THROUGHPUT_PNG_FILE}")


def PlotOverhead(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axis = plt.subplots(figsize=(8, 5))

    figure.suptitle(
        "AES-GCM vs ASCON (Ciphertext Overhead vs Payload Size)",
        fontsize=13,
    )

    for algorithm in ALGORITHMS:

        percentages: list[float] = []
        sizes: list[int] = []

        for payloadSize in PAYLOAD_SIZES:

            benchmarkCaseId: str = f"encrypt/{algorithm}/{payloadSize}"
            metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
            if metrics is None:
                continue

            overheadBytes: float = Mean(metrics.OverheadBytes)
            overheadPercent: float = overheadBytes / payloadSize * 100.0

            sizes.append(payloadSize)
            percentages.append(overheadPercent)

        axis.plot(
            sizes,
            percentages,
            label=algorithm,
            color=GetAlgorithmColor(algorithm),
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    axis.set_xlabel("Payload size")
    axis.set_ylabel("Ciphertext overhead (% of payload)")
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xticks(PAYLOAD_SIZES)
    axis.xaxis.set_major_formatter(
        FuncFormatter(lambda value, _: FormatBytes(int(value)))
    )
    axis.tick_params(axis="x", rotation=30)
    axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
    axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(OVERHEAD_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {OVERHEAD_PNG_FILE}")


def BuildHtmlTable(results: dict[str, BenchmarkMetrics]) -> str:

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Op</th>")
    lines.append("<th>Algorithm</th>")
    lines.append("<th>Payload</th>")
    lines.append("<th>Latency (ns/op)</th>")
    lines.append("<th>Throughput (MB/s)</th>")
    lines.append("<th>Overhead (B)</th>")
    lines.append("<th>Encrypted Size (B)</th>")
    lines.append("<th>Overhead (%)</th>")
    lines.append("<th>Iters (Σ8 runs)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for operation in OPERATIONS:

        for algorithm in ALGORITHMS:

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                latencyMean, latencyCI = MeanAndCI(metrics.NsPerOperation)

                throughput: float = 0.0

                if len(metrics.MbPerSecond) > 0:
                    throughput = Mean(metrics.MbPerSecond)

                overhead: float = 0.0

                if len(metrics.OverheadBytes) > 0:
                    overhead = Mean(metrics.OverheadBytes)

                encryptedSize: float = float(payloadSize) + overhead

                overheadPercent: float = 0.0

                if payloadSize > 0:
                    overheadPercent = overhead / float(payloadSize) * 100.0

                caseIterations: int = 0

                for iterationCount in metrics.Iterations:
                    caseIterations += iterationCount

                latencyText: str = f"{latencyMean:.2f} ± {latencyCI:.2f}"

                overheadText: str = "—"

                if overhead != 0.0:
                    overheadText = f"{overhead:.0f}"

                lines.append("<tr>")
                lines.append(f"<td>{operation}</td>")
                lines.append(f"<td>{algorithm}</td>")
                lines.append(f"<td>{FormatBytes(payloadSize)}</td>")
                lines.append(f"<td>{latencyText}</td>")
                lines.append(f"<td>{throughput:.1f}</td>")
                lines.append(f"<td>{overheadText}</td>")
                lines.append(f"<td>{encryptedSize:.0f}</td>")
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

    htmlTable: str = BuildHtmlTable(results)

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95_D7))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")
    report = report.replace("{{SummaryTable}}", htmlTable)
    report = report.replace("{{LatencyPlot}}", "plot.png")
    report = report.replace("{{ThroughputPlot}}", "throughput.png")
    report = report.replace("{{OverheadPlot}}", "overhead.png")

    with open(HTML_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {HTML_FILE}")


def Main() -> None:

    try:
        results: dict[str, BenchmarkMetrics] = ParseBenchmarkFile(BENCH_FILE)
    except FileNotFoundError:
        sys.exit(f"[error] {BENCH_FILE} not found — run the benchmark first")

    PlotLatency(results)
    PlotThroughput(results)
    PlotOverhead(results)
    WriteHtmlReport(results)


if __name__ == "__main__":
    Main()
