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
ASYMMETRY_PNG_FILE: str = "/results/payload-scaling/asymmetry.png"
HTML_FILE: str = "/results/payload-scaling/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/payload_scaling_template.html"

RUNS: int = int(os.environ["PAYLOAD_SCALING_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)
PAYLOAD_SIZES: list[int] = ParseIntListFromEnv("PAYLOAD_SCALING_PAYLOAD_SIZES")
SCHEMES: list[str] = ["PSK", "RSA", "CPABE"]
OPERATIONS: list[str] = ["encrypt", "decrypt"]

PSK_COLOR: str = "#0b7a3d"
RSA_COLOR: str = "#300bb6"
CPABE_COLOR: str = "#be0c24"


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


def FormatLatencyMicroseconds(latencyMicroseconds: float) -> str:

    # Keep one unit everywhere so labels are directly comparable.
    return f"{latencyMicroseconds:.1f} µs"


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

    # Payload sizes are powers of two, so a base-2 log axis spaces the points evenly.
    axis.set_xscale("log", base=2)
    axis.set_xticks(PAYLOAD_SIZES)
    # Short unit labels, rotated, so the largest sizes stop overlapping each other.
    axis.set_xticklabels(
        [FormatPayloadSizeLabel(payloadSize) for payloadSize in PAYLOAD_SIZES],
        rotation=30,
        ha="right",
    )
    # Minor log ticks would clutter the axis between the explicit size labels.
    axis.minorticks_off()


def PlotLatency(results: dict[str, BenchmarkMetrics]) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(
        "PSK vs RSA vs CP-ABE (Latency vs Payload Size)",
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

                latencyMean, latencyCI = MeanAndConfidenceInterval(
                    metrics.NsPerOperation, T_95
                )

                sizes.append(payloadSize)
                means.append(latencyMean / 1000.0)
                ciHalfs.append(latencyCI / 1000.0)

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
        axis.set_ylabel("Latency (µs) ± 95% CI")
        # Log scale: CP-ABE sits orders of magnitude above the symmetric-only PSK path.
        axis.set_yscale("log")
        ConfigurePayloadAxis(axis)
        axis.grid(True, which="both", linestyle="--", linewidth=0.5, alpha=0.6)
        axis.legend(fontsize=10)

    plt.tight_layout()
    plt.savefig(PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {PNG_FILE}")


def PlotAsymmetry(results: dict[str, BenchmarkMetrics]) -> None:

    # Smallest payload isolates the fixed asymmetric cost from the AES per-byte cost.
    referencePayloadSize: int = PAYLOAD_SIZES[0]

    figure, axis = plt.subplots(figsize=(8, 5))

    figure.suptitle(
        f"Encrypt vs Decrypt Asymmetry (payload {referencePayloadSize} B)",
        fontsize=13,
    )

    barWidth: float = 0.35

    maxLatency: float = 0.0

    for schemeIndex, schemeName in enumerate(SCHEMES):

        encryptMetrics: BenchmarkMetrics = results[
            f"encrypt/{schemeName}/{referencePayloadSize}"
        ]
        decryptMetrics: BenchmarkMetrics = results[
            f"decrypt/{schemeName}/{referencePayloadSize}"
        ]

        encryptMicroseconds: float = Mean(encryptMetrics.NsPerOperation) / 1000.0
        decryptMicroseconds: float = Mean(decryptMetrics.NsPerOperation) / 1000.0

        schemeColor: str = GetSchemeColor(schemeName)

        # Solid bar = encrypt.
        encryptBar = axis.bar(
            schemeIndex - barWidth / 2.0,
            encryptMicroseconds,
            width=barWidth,
            color=schemeColor,
            edgecolor="#182230",
            linewidth=0.8,
        )

        # Faded bar = decrypt.
        decryptBar = axis.bar(
            schemeIndex + barWidth / 2.0,
            decryptMicroseconds,
            width=barWidth,
            color=schemeColor,
            alpha=0.45,
            edgecolor="#182230",
            linewidth=0.8,
        )

        # Show both values in microseconds only.
        axis.annotate(
            FormatLatencyMicroseconds(encryptMicroseconds),
            xy=(schemeIndex - barWidth / 2.0, encryptMicroseconds),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=10,
        )

        axis.annotate(
            FormatLatencyMicroseconds(decryptMicroseconds),
            xy=(schemeIndex + barWidth / 2.0, decryptMicroseconds),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            fontsize=10,
        )

        # State the ratio explicitly, since the log-scale bars do not visually show it linearly.
        if decryptMicroseconds > encryptMicroseconds:
            asymmetryRatio: float = decryptMicroseconds / encryptMicroseconds
            asymmetryText: str = f"decrypt {asymmetryRatio:.0f}× slower"
        else:
            asymmetryRatio = encryptMicroseconds / decryptMicroseconds
            asymmetryText = f"encrypt {asymmetryRatio:.0f}× slower"

        tallerBarHeight: float = max(encryptMicroseconds, decryptMicroseconds)

        axis.annotate(
            asymmetryText,
            xy=(schemeIndex, tallerBarHeight),
            xytext=(0, 22),
            textcoords="offset points",
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

        maxLatency = max(maxLatency, tallerBarHeight)

    axis.set_xticks(range(len(SCHEMES)))
    axis.set_xticklabels(SCHEMES)
    axis.set_xlabel("Scheme")
    axis.set_ylabel("Latency (µs)")

    # Keep log scale so PSK, RSA, and CP-ABE remain simultaneously visible.
    axis.set_yscale("log")

    # Add headroom so top annotations are not clipped.
    axis.set_ylim(top=maxLatency * 12.0)

    axis.legend(
        [encryptBar, decryptBar],
        ["Encrypt", "Decrypt"],
        fontsize=10,
    )

    plt.tight_layout()
    plt.savefig(ASYMMETRY_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {ASYMMETRY_PNG_FILE}")


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
    report = report.replace("{{AsymmetryPlot}}", "asymmetry.png")

    with open(HTML_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {HTML_FILE}")


def Main() -> None:

    try:
        results: dict[str, BenchmarkMetrics] = ParseBenchmarkFile(BENCH_FILE)
    except FileNotFoundError:
        sys.exit(f"[error] {BENCH_FILE} not found — run the benchmark first")

    PlotLatency(results)
    PlotAsymmetry(results)
    WriteHtmlReport(results)


if __name__ == "__main__":
    Main()
