import matplotlib
import os

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from utils.statistics import GetStudentTCriticalValue95
from utils.statistics import Mean
from utils.statistics import MeanAndConfidenceInterval
from utils.parser import ParseIntListFromEnv

BENCH_FILE: str = "/results/payload-scaling/bench_output.txt"
PNG_FILE: str = "/results/payload-scaling/plot.png"
THROUGHPUT_PNG_FILE: str = "/results/payload-scaling/throughput.png"
HTML_FILE: str = "/results/payload-scaling/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/payload_scaling_template.html"

RUNS: int = int(os.environ["PAYLOAD_SCALING_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)
PAYLOAD_SIZES: list[int] = ParseIntListFromEnv("PAYLOAD_SCALING_PAYLOAD_SIZES")
SCHEMES: list[str] = ["PSK", "RSA", "CPABE"]
OPERATIONS: list[str] = ["encrypt", "decrypt"]

PSK_COLOR: str = "#0f766e"
RSA_COLOR: str = "#7c3aed"
CPABE_COLOR: str = "#c2415d"


class BenchmarkMetrics:

    def __init__(
        self,
        operation: str,
        schemeName: str,
        payloadSize: int,
    ) -> None:

        self.Operation: str = operation
        self.Scheme: str = schemeName
        self.PayloadSize: int = payloadSize

        self.Iterations: list[int] = []
        self.NsPerOperation: list[float] = []
        self.MbPerSecond: list[float] = []
        self.WireOverheadBytes: list[float] = []


def GetSchemeColor(schemeName: str) -> str:
    if schemeName == "PSK":
        return PSK_COLOR

    if schemeName == "RSA":
        return RSA_COLOR

    return CPABE_COLOR


def ParseBenchmarkFile(filepath: str) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    prefix: str = "BenchmarkPayloadScaling"

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields: list[str] = line.strip().split()

            if len(fields) == 0:
                continue

            benchmarkName: str = fields[0]

            if not benchmarkName.startswith(prefix):
                continue

            # "Encrypt/PSK/64B-1" -> operation, scheme, payload size text.
            operation, schemeName, payloadSizeText, *_ = benchmarkName[
                len(prefix) :
            ].split("/")
            operation = operation.lower()

            # Strip GOMAXPROCS suffix (e.g. "-1") first, then the "B" unit label.
            payloadSize: int = int(payloadSizeText.split("-")[0].replace("B", ""))

            benchmarkCaseId: str = f"{operation}/{schemeName}/{payloadSize}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    schemeName,
                    payloadSize,
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
            metrics.MbPerSecond.append(metricsByUnit["MB/s"])

            # Wire overhead is only reported by the encrypt benchmark, decrypt lines lack it.
            if "wire_overhead_bytes/op" in metricsByUnit:
                metrics.WireOverheadBytes.append(
                    metricsByUnit["wire_overhead_bytes/op"]
                )

    return results


def GetSchemeOverheadBytes(
    results: dict[str, BenchmarkMetrics],
    schemeName: str,
) -> float:

    # Overhead is a fixed per-scheme constant, so pooling every encrypt case's
    # samples and taking the mean just recovers that constant.
    overheadSamples: list[float] = []

    for payloadSize in PAYLOAD_SIZES:

        metrics: BenchmarkMetrics | None = results.get(
            f"encrypt/{schemeName}/{payloadSize}"
        )
        if metrics is None:
            continue

        overheadSamples.extend(metrics.WireOverheadBytes)

    return Mean(overheadSamples)


def FormatPayloadSizeLabel(payloadSizeBytes: int) -> str:

    # Short human units keep axis labels readable.
    if payloadSizeBytes >= 1024 * 1024:
        return f"{payloadSizeBytes // (1024 * 1024)}MB"

    if payloadSizeBytes >= 1024:
        return f"{payloadSizeBytes // 1024}KB"

    return f"{payloadSizeBytes}B"


def FormatByteSize(byteCount: int) -> str:

    # Display large table values in megabytes while preserving small overhead differences.
    if byteCount >= 1024 * 1024:
        megabytes: float = byteCount / float(1024 * 1024)
        formattedMegabytes: str = f"{megabytes:.4f}".rstrip("0").rstrip(".")
        return f"{formattedMegabytes} MB"

    # Display medium table values in kilobytes.
    if byteCount >= 1024:
        kilobytes: float = byteCount / float(1024)
        formattedKilobytes: str = f"{kilobytes:.2f}".rstrip("0").rstrip(".")
        return f"{formattedKilobytes} KB"

    return f"{byteCount} B"


def ConfigurePayloadAxis(axis) -> None:

    # Keep payload position proportional to the actual number of bytes.
    maxPayloadSize: int = PAYLOAD_SIZES[-1]

    # Use regular 4 MiB ticks so the linear axis remains readable.
    tickStep: int = 4 * 1024 * 1024
    tickValues: list[int] = list(range(0, maxPayloadSize + tickStep, tickStep))

    axis.set_xticks(tickValues)

    axis.set_xticklabels(
        [
            "0" if tickValue == 0 else FormatPayloadSizeLabel(tickValue)
            for tickValue in tickValues
        ]
    )

    axis.set_xlim(0, maxPayloadSize * 1.03)


def PlotLatency(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "PSK vs. RSA vs. CP-ABE: Latency vs. Payload Size",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        zoomAxis = None
        zoomMaximum: float = 0.0

        # CP-ABE dominates publisher latency, so add a linear zoom for PSK and RSA.
        if operation == "encrypt":
            zoomAxis = axis.inset_axes([0.08, 0.08, 0.47, 0.32])

        for schemeName in SCHEMES:

            means: list[float] = []
            ciHalfs: list[float] = []
            payloadSizes: list[int] = []

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{schemeName}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
                if metrics is None:
                    continue

                latencyMean: float
                latencyCI: float

                latencyMean, latencyCI = MeanAndConfidenceInterval(
                    metrics.NsPerOperation,
                    T_95,
                )

                meanMicroseconds: float = latencyMean / 1000.0
                ciMicroseconds: float = latencyCI / 1000.0

                payloadSizes.append(payloadSize)
                means.append(meanMicroseconds)
                ciHalfs.append(ciMicroseconds)

            axis.errorbar(
                payloadSizes,
                means,
                yerr=ciHalfs,
                label=schemeName,
                color=GetSchemeColor(schemeName),
                marker="o",
                linewidth=1.8,
                markersize=5,
                capsize=4,
            )

            # Repeat only the lower-latency schemes inside the Encrypt zoom.
            if zoomAxis is not None and schemeName != "CPABE":

                zoomAxis.errorbar(
                    payloadSizes,
                    means,
                    yerr=ciHalfs,
                    label=schemeName,
                    color=GetSchemeColor(schemeName),
                    marker="o",
                    linewidth=1.6,
                    markersize=4,
                    capsize=3,
                )

                for meanMicroseconds, ciMicroseconds in zip(means, ciHalfs):
                    zoomMaximum = max(
                        zoomMaximum,
                        meanMicroseconds + ciMicroseconds,
                    )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Latency (µs) ± 95% CI")

        # Keep the main graph genuinely linear and zero-based.
        axis.set_ylim(bottom=0)

        ConfigurePayloadAxis(axis)

        axis.grid(
            True,
            axis="y",
            linestyle="-",
            linewidth=0.5,
            alpha=0.18,
        )

        axis.legend(
            fontsize=10,
            loc="upper left",
        )

        if zoomAxis is not None:

            # Keep the zoom linear and zero-based as well.
            zoomAxis.set_ylim(0.0, zoomMaximum * 1.10)
            zoomAxis.set_xlim(0, PAYLOAD_SIZES[-1] * 1.03)
            zoomAxis.set_xticks([])

            zoomAxis.set_title(
                "PSK + RSA Zoom",
                fontsize=9,
            )

            zoomAxis.set_ylabel(
                "µs",
                fontsize=8,
            )

            zoomAxis.tick_params(
                axis="both",
                labelsize=8,
            )

            zoomAxis.grid(
                True,
                axis="y",
                linestyle="-",
                linewidth=0.4,
                alpha=0.18,
            )

            zoomAxis.legend(
                fontsize=8,
                loc="upper left",
            )

    plt.tight_layout()
    plt.savefig(PNG_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)

    print(f"Saved -> {PNG_FILE}")


def PlotThroughput(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "PSK vs. RSA vs. CP-ABE: Throughput vs. Payload Size",
        fontsize=13,
    )

    for axis, operation in zip(axes, OPERATIONS):

        for schemeName in SCHEMES:

            means: list[float] = []
            ciHalfs: list[float] = []
            sizes: list[int] = []

            for payloadSize in PAYLOAD_SIZES:

                benchmarkCaseId: str = f"{operation}/{schemeName}/{payloadSize}"
                metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

                if metrics is None:
                    continue

                throughputMean: float
                throughputCI: float

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
                label=schemeName,
                color=GetSchemeColor(schemeName),
                marker="o",
                linewidth=1.8,
                markersize=5,
                capsize=4,
            )

        axis.set_title(operation.capitalize(), fontsize=11)
        axis.set_xlabel("Payload size")
        axis.set_ylabel("Throughput (MB/s) ± 95% CI")

        # Keep throughput visually proportional to the measured MB/s values.
        axis.set_ylim(bottom=0)

        # Reuse the exact payload-axis policy already used by Scenario 1.
        ConfigurePayloadAxis(axis)

        axis.grid(
            True,
            axis="y",
            linestyle="-",
            linewidth=0.5,
            alpha=0.18,
        )

        axis.legend(
            fontsize=10,
            loc="upper left",
        )

    plt.tight_layout()
    plt.savefig(
        THROUGHPUT_PNG_FILE,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(figure)

    print(f"Saved -> {THROUGHPUT_PNG_FILE}")


def BuildOperationSchemeTable(
    results: dict[str, BenchmarkMetrics],
    operation: str,
    schemeName: str,
) -> str:

    # The same fixed cryptographic envelope is used in both directions.
    overheadBytesValue: float = GetSchemeOverheadBytes(results, schemeName)

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append("<th>Raw Size</th>")
    lines.append("<th>Latency (µs/op)</th>")
    lines.append("<th>Wire Size</th>")
    lines.append("<th>Overhead (%)</th>")
    lines.append(f"<th>Iters (Σ{RUNS} runs)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for payloadSize in PAYLOAD_SIZES:

        benchmarkCaseId: str = f"{operation}/{schemeName}/{payloadSize}"
        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
        if metrics is None:
            continue

        latencyMean: float
        latencyCI: float

        latencyMean, latencyCI = MeanAndConfidenceInterval(
            metrics.NsPerOperation,
            T_95,
        )

        # Convert the measured fixed overhead back to an integer byte count.
        overheadBytes: int = int(round(overheadBytesValue))

        # Add the fixed cryptographic overhead to the raw payload.
        wireSizeBytes: int = payloadSize + overheadBytes

        # Express the added bytes relative to the original raw payload.
        overheadPercent: float = overheadBytes / payloadSize * 100.0

        # Avoid displaying a small nonzero overhead as 0.00%.
        if overheadPercent < 0.01:
            overheadText: str = "&lt;0.01%"
        else:
            overheadText = f"{overheadPercent:.2f}%"

        caseIterations: int = 0

        for iterationCount in metrics.Iterations:
            caseIterations += iterationCount

        # Convert Go's nanoseconds per operation to microseconds.
        latencyText: str = f"{latencyMean / 1000.0:.2f} ± " f"{latencyCI / 1000.0:.2f}"

        lines.append("<tr>")
        lines.append(f"<td>{FormatByteSize(payloadSize)}</td>")
        lines.append(f"<td>{latencyText}</td>")
        lines.append(f"<td>{FormatByteSize(wireSizeBytes)}</td>")
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

    # Six filtered tables — one per operation/scheme pair.
    encryptPskTable: str = BuildOperationSchemeTable(results, "encrypt", "PSK")
    encryptRsaTable: str = BuildOperationSchemeTable(results, "encrypt", "RSA")
    encryptCpabeTable: str = BuildOperationSchemeTable(results, "encrypt", "CPABE")
    decryptPskTable: str = BuildOperationSchemeTable(results, "decrypt", "PSK")
    decryptRsaTable: str = BuildOperationSchemeTable(results, "decrypt", "RSA")
    decryptCpabeTable: str = BuildOperationSchemeTable(results, "decrypt", "CPABE")

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")
    report = report.replace("{{EncryptPskTable}}", encryptPskTable)
    report = report.replace("{{EncryptRsaTable}}", encryptRsaTable)
    report = report.replace("{{EncryptCpabeTable}}", encryptCpabeTable)
    report = report.replace("{{DecryptPskTable}}", decryptPskTable)
    report = report.replace("{{DecryptRsaTable}}", decryptRsaTable)
    report = report.replace("{{DecryptCpabeTable}}", decryptCpabeTable)
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
