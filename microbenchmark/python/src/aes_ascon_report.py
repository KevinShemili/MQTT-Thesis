import matplotlib
import os

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from utils.parser import ParseIntListFromEnv
from utils.statistics import GetStudentTCriticalValue95
from utils.statistics import Mean
from utils.statistics import MeanAndConfidenceInterval

RESULT_DIR: str = os.environ.get("AES_ASCON_RESULT_DIR", "/results/aes-ascon")

BENCH_FILE: str = os.path.join(RESULT_DIR, "bench_output.txt")
PNG_FILE: str = os.path.join(RESULT_DIR, "plot.png")
THROUGHPUT_PNG_FILE: str = os.path.join(RESULT_DIR, "throughput.png")
HTML_FILE: str = os.path.join(RESULT_DIR, "report.html")
HTML_TEMPLATE_FILE: str = "/app/template/aes_ascon_template.html"

RUNS: int = int(os.environ["AES_ASCON_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)

PAYLOAD_SIZES: list[int] = ParseIntListFromEnv("AES_ASCON_PAYLOAD_SIZES")
ALGORITHMS: list[str] = ["AES-GCM", "ASCON"]
OPERATIONS: list[str] = ["encrypt", "decrypt"]

AES_GCM_COLOR: str = "#be0c24"
ASCON_COLOR: str = "#300bb6"


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

    prefix: str = "BenchmarkAESASCON"

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields: list[str] = line.strip().split()

            if len(fields) == 0:
                continue

            benchmarkName: str = fields[0]

            if not benchmarkName.startswith(prefix):
                continue

            benchmarkParts: list[str] = benchmarkName[len(prefix) :].split("/")

            operation: str = benchmarkParts[0].lower()
            algorithm: str = benchmarkParts[1]
            payloadText: str = benchmarkParts[2]

            payloadSize: int = int(payloadText.split("-")[0].replace("B", ""))

            benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    algorithm,
                    payloadSize,
                )

            metrics: BenchmarkMetrics = results[benchmarkCaseId]

            iterationCount: int = int(fields[1])

            metricsByUnit: dict[str, float] = {}

            for index in range(2, len(fields) - 1, 2):
                unitName: str = fields[index + 1]
                metricsByUnit[unitName] = float(fields[index])

            metrics.Iterations.append(iterationCount)
            metrics.NsPerOperation.append(metricsByUnit["ns/op"])
            metrics.MbPerSecond.append(metricsByUnit["MB/s"])
            metrics.OverheadBytes.append(metricsByUnit["wire_overhead_bytes/op"])

    return results


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

                latencyMean, latencyCI = MeanAndConfidenceInterval(
                    metrics.NsPerOperation,
                    T_95,
                )

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
            ciHalfs: list[float] = []
            sizes: list[int] = []

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

                if metrics is None:
                    continue

                throughputMean, throughputCI = MeanAndConfidenceInterval(
                    metrics.MbPerSecond,
                    T_95,
                )

                sizes.append(payloadSize)
                means.append(throughputMean)
                ciHalfs.append(throughputCI)

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
        axis.set_ylabel("Throughput (MB/s) ± 95% CI")
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


def BuildOperationAlgorithmTable(
    results: dict[str, BenchmarkMetrics],
    operation: str,
    algorithm: str,
) -> str:

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Payload</th>")
    lines.append("<th>Latency (ns/op)</th>")
    lines.append("<th>Throughput (MB/s)</th>")
    lines.append("<th>Tag + Nonce (B)</th>")
    lines.append(f"<th>Iters (Σ{RUNS} runs)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for payloadSize in PAYLOAD_SIZES:

        benchmarkCaseId: str = f"{operation}/{algorithm}/{payloadSize}"
        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

        if metrics is None:
            continue

        latencyMean, latencyCI = MeanAndConfidenceInterval(
            metrics.NsPerOperation,
            T_95,
        )

        throughput: float = 0.0
        throughputCI: float = 0.0

        if len(metrics.MbPerSecond) > 0:
            throughput, throughputCI = MeanAndConfidenceInterval(
                metrics.MbPerSecond,
                T_95,
            )

        overhead: float = 0.0

        if len(metrics.OverheadBytes) > 0:
            overhead = Mean(metrics.OverheadBytes)

        caseIterations: int = 0

        for iterationCount in metrics.Iterations:
            caseIterations += iterationCount

        latencyText: str = f"{latencyMean:.2f} ± {latencyCI:.2f}"
        throughputText: str = f"{throughput:.1f} ± {throughputCI:.1f}"

        overheadText: str = "—"

        if overhead != 0.0:
            overheadText = f"{overhead:.0f}"

        lines.append("<tr>")
        lines.append(f"<td>{FormatBytes(payloadSize)}</td>")
        lines.append(f"<td>{latencyText}</td>")
        lines.append(f"<td>{throughputText}</td>")
        lines.append(f"<td>{overheadText}</td>")
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

    encryptAesTable: str = BuildOperationAlgorithmTable(
        results,
        "encrypt",
        "AES-GCM",
    )

    encryptAsconTable: str = BuildOperationAlgorithmTable(
        results,
        "encrypt",
        "ASCON",
    )

    decryptAesTable: str = BuildOperationAlgorithmTable(
        results,
        "decrypt",
        "AES-GCM",
    )

    decryptAsconTable: str = BuildOperationAlgorithmTable(
        results,
        "decrypt",
        "ASCON",
    )

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")
    report = report.replace("{{EncryptAesTable}}", encryptAesTable)
    report = report.replace("{{EncryptAsconTable}}", encryptAsconTable)
    report = report.replace("{{DecryptAesTable}}", decryptAesTable)
    report = report.replace("{{DecryptAsconTable}}", decryptAsconTable)
    report = report.replace("{{LatencyPlot}}", "plot.png")
    report = report.replace("{{ThroughputPlot}}", "throughput.png")

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
    WriteHtmlReport(results)


if __name__ == "__main__":
    Main()
