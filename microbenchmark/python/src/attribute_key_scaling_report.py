import matplotlib
import os

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from utils.statistics import GetStudentTCriticalValue95
from utils.statistics import Mean
from utils.statistics import MeanAndConfidenceInterval
from utils.parser import ParseIntListFromEnv

BENCH_FILE: str = "/results/attribute-key-scaling/bench_output.txt"
CPABE_PNG_FILE: str = "/results/attribute-key-scaling/cpabe_attributes.png"
RSA_SUBSCRIBERS_PNG_FILE: str = "/results/attribute-key-scaling/rsa_subscribers.png"
RSA_KEY_BITS_PNG_FILE: str = "/results/attribute-key-scaling/rsa_key_bits.png"
BANDWIDTH_CROSSOVER_PNG_FILE: str = (
    "/results/attribute-key-scaling/bandwidth_crossover.png"
)
ASYMMETRY_PNG_FILE: str = "/results/attribute-key-scaling/encrypt_decrypt_asymmetry.png"
HTML_FILE: str = "/results/attribute-key-scaling/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/attribute_key_scaling_template.html"

RUNS: int = int(os.environ["ATTRIBUTE_KEY_SCALING_RUNS"])
T_95: float = GetStudentTCriticalValue95(RUNS - 1)
ATTRIBUTE_COUNTS: list[int] = ParseIntListFromEnv(
    "ATTRIBUTE_KEY_SCALING_ATTRIBUTE_COUNT"
)
SUBSCRIBER_COUNTS: list[int] = ParseIntListFromEnv(
    "ATTRIBUTE_KEY_SCALING_SUBSCRIBER_COUNT"
)
RSA_KEY_BITS_LIST: list[int] = ParseIntListFromEnv(
    "ATTRIBUTE_KEY_SCALING_RSA_KEY_SIZES"
)
FIXED_RSA_KEY_BITS: int = int(os.environ["ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS"])
OPERATIONS: list[str] = ["encrypt", "decrypt", "keygen"]

ENCRYPT_COLOR: str = "#d97706"
DECRYPT_COLOR: str = "#7c3aed"
KEYGEN_COLOR: str = "#c2415d"
TOTAL_CIPHERTEXT_COLOR: str = "#0f766e"

# Fan-out circles: the larger circle is drawn at a fixed size and the smaller one is scaled
# against it, with a floor so a tiny ratio still leaves something visible on screen.
FANOUT_LARGEST_DIAMETER_PX: float = 168.0
FANOUT_SMALLEST_DIAMETER_PX: float = 22.0


class BenchmarkMetrics:

    def __init__(
        self,
        operation: str,
        sweepName: str,
        sweepValue: int,
    ) -> None:

        self.Operation: str = operation
        self.Sweep: str = sweepName
        self.SweepValue: int = sweepValue

        self.Iterations: list[int] = []
        self.NsPerOperation: list[float] = []
        self.SingleCiphertextBytes: list[float] = []
        self.TotalCiphertextBytes: list[float] = []
        self.StoredKeyBytes: list[float] = []


class CrossoverSummary:

    def __init__(self) -> None:

        # RSA fan-out inputs measured across the subscriber sweep.
        self.MeasuredSubscribers: list[float] = []
        self.MeasuredTotalBytes: list[float] = []
        self.RsaSingleBytes: float = 0.0

        # CP-ABE ciphertext sizes at the smallest and largest tested policies.
        self.CpabeBytesMin: float = 0.0
        self.CpabeBytesMax: float = 0.0

        # Audience sizes where measured byte-growth relationships are equal.
        self.BytesCrossoverMin: float = 0.0
        self.BytesCrossoverMax: float = 0.0


def GetOperationColor(operation: str) -> str:
    if operation == "encrypt":
        return ENCRYPT_COLOR

    if operation == "decrypt":
        return DECRYPT_COLOR

    return KEYGEN_COLOR


def ParseBenchmarkFile(filepath: str) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    prefix: str = "BenchmarkAttributeKeyScaling"

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields: list[str] = line.strip().split()

            if len(fields) == 0:
                continue

            benchmarkName: str = fields[0]

            if not benchmarkName.startswith(prefix):
                continue

            # "Encrypt/CPABEAttributes/8-1" -> operation, sweep name, sweep value text.
            operation, sweepName, sweepValueText, *_ = benchmarkName[
                len(prefix) :
            ].split("/")
            operation = operation.lower()

            # Strip the GOMAXPROCS suffix (e.g. "-1"); the sweep value carries no unit label.
            sweepValue: int = int(sweepValueText.split("-")[0])

            benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics(
                    operation,
                    sweepName,
                    sweepValue,
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

            # Single-ciphertext and total-ciphertext bytes are only reported by the encrypt benchmark.
            if "ciphertext_bytes" in metricsByUnit:
                metrics.SingleCiphertextBytes.append(metricsByUnit["ciphertext_bytes"])

            if "total_ciphertext_bytes" in metricsByUnit:
                metrics.TotalCiphertextBytes.append(
                    metricsByUnit["total_ciphertext_bytes"]
                )

            # Stored key bytes is only reported by the keygen benchmark.
            if "stored_key_bytes" in metricsByUnit:
                metrics.StoredKeyBytes.append(metricsByUnit["stored_key_bytes"])

    return results


def FormatByteSize(byteCount: int) -> str:

    # Display large table values in megabytes while preserving small size differences.
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


def FormatAttributeLabel(attributeCount: int) -> str:

    if attributeCount == 1:
        return "1 ATTRIBUTE"

    return f"{attributeCount} ATTRIBUTES"


def GetMeanLatencyMicros(
    results: dict[str, BenchmarkMetrics],
    benchmarkCaseId: str,
) -> float:

    metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

    if metrics is None or len(metrics.NsPerOperation) == 0:
        sys.exit(f"[error] missing benchmark case '{benchmarkCaseId}' in {BENCH_FILE}")

    # Convert Go's nanoseconds per operation to microseconds.
    return Mean(metrics.NsPerOperation) / 1000.0


def GetMeanSingleCiphertextBytes(
    results: dict[str, BenchmarkMetrics],
    benchmarkCaseId: str,
) -> float:

    metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

    if metrics is None or len(metrics.SingleCiphertextBytes) == 0:
        sys.exit(
            f"[error] missing ciphertext bytes for '{benchmarkCaseId}' in {BENCH_FILE}"
        )

    return Mean(metrics.SingleCiphertextBytes)


def GetMeanTotalCiphertextBytes(
    results: dict[str, BenchmarkMetrics],
    benchmarkCaseId: str,
) -> float:

    metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

    if metrics is None or len(metrics.TotalCiphertextBytes) == 0:
        sys.exit(
            f"[error] missing total ciphertext bytes for '{benchmarkCaseId}' in {BENCH_FILE}"
        )

    return Mean(metrics.TotalCiphertextBytes)


def FitLinear(xValues: list[float], yValues: list[float]) -> tuple[float, float]:

    xMean: float = Mean(xValues)
    yMean: float = Mean(yValues)

    numerator: float = 0.0
    denominator: float = 0.0

    # Ordinary least squares: slope = covariance(x, y) / variance(x).
    for index in range(len(xValues)):
        numerator += (xValues[index] - xMean) * (yValues[index] - yMean)
        denominator += (xValues[index] - xMean) ** 2

    slope: float = numerator / denominator
    intercept: float = yMean - slope * xMean

    return slope, intercept


def ConfigureSweepAxis(axis, sweepValues: list[int], xLabel: str) -> None:

    # Use the real numerical spacing so horizontal distance represents the actual sweep increase.
    axis.set_xticks(sweepValues)
    axis.set_xlabel(xLabel)


def PlotSweep(
    results: dict[str, BenchmarkMetrics],
    sweepName: str,
    sweepValues: list[int],
    sweepOperations: list[str],
    xLabel: str,
    figureTitle: str,
    pngFile: str,
    constantDecryptMicros: float | None = None,
) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(figureTitle, fontsize=13)

    latencyAxis = axes[0]
    sizeAxis = axes[1]

    # Left panel: latency per operation across the sweep.
    for operation in sweepOperations:

        means: list[float] = []
        ciHalfs: list[float] = []
        values: list[int] = []

        for sweepValue in sweepValues:

            benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"
            metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
            if metrics is None:
                continue

            latencyMean, latencyCI = MeanAndConfidenceInterval(
                metrics.NsPerOperation, T_95
            )

            values.append(sweepValue)
            means.append(latencyMean / 1000.0)
            ciHalfs.append(latencyCI / 1000.0)

        latencyAxis.errorbar(
            values,
            means,
            yerr=ciHalfs,
            label=operation.capitalize(),
            color=GetOperationColor(operation),
            marker="o",
            linewidth=1.8,
            markersize=5,
            capsize=4,
        )

    # Drawn flat on purpose: subscriber-side decrypt does not vary with audience size, so the
    # value comes from the key-size sweep instead of a per-N measurement that cannot move.
    if constantDecryptMicros is not None:
        latencyAxis.axhline(
            constantDecryptMicros,
            color=DECRYPT_COLOR,
            linestyle="--",
            linewidth=1.8,
            label=f"Decrypt (Constant)",
        )

    latencyAxis.set_title("Latency", fontsize=11)
    latencyAxis.set_ylabel("Latency (µs) ± 95% CI")
    latencyAxis.set_ylim(bottom=0)
    ConfigureSweepAxis(latencyAxis, sweepValues, xLabel)
    latencyAxis.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.18)
    latencyAxis.legend(fontsize=10)

    # Right panel: the interpretable memory story — bytes on the wire & bytes stored on device.
    singleCiphertextValues: list[int] = []
    singleCiphertextSizes: list[float] = []
    totalCiphertextValues: list[int] = []
    totalCiphertextSizes: list[float] = []
    storedKeyValues: list[int] = []
    storedKeySizes: list[float] = []

    for sweepValue in sweepValues:

        encryptMetrics: BenchmarkMetrics | None = results.get(
            f"encrypt/{sweepName}/{sweepValue}"
        )
        if encryptMetrics is not None and len(encryptMetrics.SingleCiphertextBytes) > 0:
            singleCiphertextValues.append(sweepValue)
            singleCiphertextSizes.append(Mean(encryptMetrics.SingleCiphertextBytes))

        # Total is only reported where it differs from single (the RSA subscriber sweep) —
        # CP-ABE and the RSA key-size sweep never emit it, since it would just duplicate single
        if encryptMetrics is not None and len(encryptMetrics.TotalCiphertextBytes) > 0:
            totalCiphertextValues.append(sweepValue)
            totalCiphertextSizes.append(Mean(encryptMetrics.TotalCiphertextBytes))

        keygenMetrics: BenchmarkMetrics | None = results.get(
            f"keygen/{sweepName}/{sweepValue}"
        )
        if keygenMetrics is not None and len(keygenMetrics.StoredKeyBytes) > 0:
            storedKeyValues.append(sweepValue)
            storedKeySizes.append(Mean(keygenMetrics.StoredKeyBytes))

    sizeAxis.plot(
        singleCiphertextValues,
        singleCiphertextSizes,
        label="Ciphertext",
        color=ENCRYPT_COLOR,
        marker="o",
        linewidth=1.8,
        markersize=5,
    )

    # Only draw the total line where it was actually reported — CP-ABE and the RSA key-size
    # sweep never emit it, since a single subscriber makes total identical to single
    if len(totalCiphertextValues) > 0:
        sizeAxis.plot(
            totalCiphertextValues,
            totalCiphertextSizes,
            label="Ciphertext (Total)",
            color=TOTAL_CIPHERTEXT_COLOR,
            marker="^",
            linewidth=1.8,
            markersize=5,
            linestyle=":",
        )

    # The keygen sweep does not run for every case, so this series may be absent.
    if len(storedKeyValues) > 0:
        sizeAxis.plot(
            storedKeyValues,
            storedKeySizes,
            label="Stored key",
            color=KEYGEN_COLOR,
            marker="s",
            linewidth=1.8,
            markersize=5,
            linestyle="--",
        )

    sizeAxis.set_title("Sizes", fontsize=11)
    sizeAxis.set_ylabel("Size (bytes)")
    # Linear axes on purpose: sizes grow linearly with the sweep, and the log-x axis used for
    # latency would visually bend that straight line into a fake exponential. Here a straight
    # line IS linear growth, and matplotlib's default linear ticks keep the labels readable.
    ConfigureSweepAxis(sizeAxis, sweepValues, xLabel)
    sizeAxis.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.18)
    sizeAxis.legend(fontsize=10)
    # Anchor at zero so proportions between the series are honest.
    sizeAxis.set_ylim(bottom=0)

    figure.tight_layout(rect=[0.0, 0.0, 1.0, 0.94])  # type: ignore
    plt.savefig(pngFile, dpi=150, bbox_inches="tight")
    print(f"Saved -> {pngFile}")


def ComputeCrossoverSummary(results: dict[str, BenchmarkMetrics]) -> CrossoverSummary:

    summary: CrossoverSummary = CrossoverSummary()

    minAttributeCount: int = ATTRIBUTE_COUNTS[0]
    maxAttributeCount: int = ATTRIBUTE_COUNTS[-1]

    # Collect the measured RSA total bytes for every tested subscriber count.
    for subscriberCount in SUBSCRIBER_COUNTS:

        metrics: BenchmarkMetrics | None = results.get(
            f"encrypt/RSASubscribers/{subscriberCount}"
        )
        if metrics is None or len(metrics.TotalCiphertextBytes) == 0:
            sys.exit(
                "[error] missing RSA subscriber sweep data for crossover synthesis"
            )

        summary.MeasuredSubscribers.append(float(subscriberCount))
        summary.MeasuredTotalBytes.append(Mean(metrics.TotalCiphertextBytes))

    summary.RsaSingleBytes = GetMeanSingleCiphertextBytes(
        results, f"encrypt/RSASubscribers/{SUBSCRIBER_COUNTS[0]}"
    )

    # One CP-ABE ciphertext serves the complete subscriber audience.
    summary.CpabeBytesMin = GetMeanSingleCiphertextBytes(
        results, f"encrypt/CPABEAttributes/{minAttributeCount}"
    )
    summary.CpabeBytesMax = GetMeanSingleCiphertextBytes(
        results, f"encrypt/CPABEAttributes/{maxAttributeCount}"
    )

    # RSA total bytes increase by exactly one wrapped key per subscriber.
    summary.BytesCrossoverMin = summary.CpabeBytesMin / summary.RsaSingleBytes
    summary.BytesCrossoverMax = summary.CpabeBytesMax / summary.RsaSingleBytes

    return summary


def ComputeCpabeMarginalSlopes(
    results: dict[str, BenchmarkMetrics],
) -> tuple[float, float, float]:

    encryptAttributeValues: list[float] = []
    encryptMicrosValues: list[float] = []
    ciphertextAttributeValues: list[float] = []
    ciphertextBytesValues: list[float] = []
    storedKeyAttributeValues: list[float] = []
    storedKeyBytesValues: list[float] = []

    for attributeCount in ATTRIBUTE_COUNTS:

        encryptMetrics: BenchmarkMetrics | None = results.get(
            f"encrypt/CPABEAttributes/{attributeCount}"
        )
        if encryptMetrics is not None and len(encryptMetrics.NsPerOperation) > 0:
            encryptAttributeValues.append(float(attributeCount))
            encryptMicrosValues.append(Mean(encryptMetrics.NsPerOperation) / 1000.0)

        if encryptMetrics is not None and len(encryptMetrics.SingleCiphertextBytes) > 0:
            ciphertextAttributeValues.append(float(attributeCount))
            ciphertextBytesValues.append(Mean(encryptMetrics.SingleCiphertextBytes))

        keygenMetrics: BenchmarkMetrics | None = results.get(
            f"keygen/CPABEAttributes/{attributeCount}"
        )
        if keygenMetrics is not None and len(keygenMetrics.StoredKeyBytes) > 0:
            storedKeyAttributeValues.append(float(attributeCount))
            storedKeyBytesValues.append(Mean(keygenMetrics.StoredKeyBytes))

    # Least-squares slope of each series against attribute count: cost of one more attribute.
    encryptSlopeMicros, _ = FitLinear(encryptAttributeValues, encryptMicrosValues)
    ciphertextSlopeBytes, _ = FitLinear(
        ciphertextAttributeValues, ciphertextBytesValues
    )
    storedKeySlopeBytes, _ = FitLinear(storedKeyAttributeValues, storedKeyBytesValues)

    return encryptSlopeMicros, ciphertextSlopeBytes, storedKeySlopeBytes


def ComputeRsaSubscriberMarginalSlopes(
    results: dict[str, BenchmarkMetrics],
) -> tuple[float, float, float]:

    subscriberValues: list[float] = []
    encryptMicrosValues: list[float] = []
    totalCiphertextBytesValues: list[float] = []
    decryptMicrosValues: list[float] = []

    rsaDecryptMicros: float = GetMeanLatencyMicros(
        results, f"decrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}"
    )

    for subscriberCount in SUBSCRIBER_COUNTS:

        encryptMetrics: BenchmarkMetrics | None = results.get(
            f"encrypt/RSASubscribers/{subscriberCount}"
        )
        if encryptMetrics is None:
            continue

        subscriberValues.append(float(subscriberCount))
        encryptMicrosValues.append(Mean(encryptMetrics.NsPerOperation) / 1000.0)
        totalCiphertextBytesValues.append(Mean(encryptMetrics.TotalCiphertextBytes))

        # One subscriber always unwraps one session key, regardless of total audience size.
        decryptMicrosValues.append(rsaDecryptMicros)

    # Each slope is the approximate change caused by one additional subscriber.
    encryptSlopeMicros, _ = FitLinear(subscriberValues, encryptMicrosValues)
    totalCiphertextSlopeBytes, _ = FitLinear(
        subscriberValues, totalCiphertextBytesValues
    )
    decryptSlopeMicros, _ = FitLinear(subscriberValues, decryptMicrosValues)

    # Avoid displaying negative zero when the fitted constant series is numerically flat.
    if abs(decryptSlopeMicros) < 0.000001:
        decryptSlopeMicros = 0.0

    return encryptSlopeMicros, totalCiphertextSlopeBytes, decryptSlopeMicros


def DrawCrossoverPanel(
    axis,
    measuredSubscribers: list[float],
    measuredValues: list[float],
    cpabeMinValue: float,
    cpabeMaxValue: float,
    crossoverMin: float,
    crossoverMax: float,
    xLimit: int,
) -> None:

    # Plot only values observed in the RSA subscriber sweep.
    axis.plot(
        measuredSubscribers,
        measuredValues,
        color=TOTAL_CIPHERTEXT_COLOR,
        marker="^",
        linewidth=1.8,
        markersize=5,
        label="RSA Scaling Subs",
    )

    # One CP-ABE ciphertext serves the complete subscriber audience.
    axis.hlines(
        cpabeMinValue,
        1,
        xLimit,
        color=ENCRYPT_COLOR,
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[0])}",
    )
    axis.hlines(
        cpabeMaxValue,
        1,
        xLimit,
        color=KEYGEN_COLOR,
        linestyle="-.",
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[-1])}",
    )

    # Mark the subscriber counts where the byte totals are equal.
    for crossoverValue, levelValue in (
        (crossoverMin, cpabeMinValue),
        (crossoverMax, cpabeMaxValue),
    ):
        axis.plot(
            [crossoverValue],
            [levelValue],
            marker="X",
            color="black",
            markersize=9,
            linestyle="none",
            zorder=5,
        )
        axis.annotate(
            f"≈{crossoverValue:,.1f}",
            (crossoverValue, levelValue),
            textcoords="offset points",
            xytext=(6, 8),
            fontsize=9,
            fontweight="bold",
        )

    linearTickValues: list[int] = [SUBSCRIBER_COUNTS[0]]
    for subscriberCount in SUBSCRIBER_COUNTS:
        if subscriberCount >= 8:
            linearTickValues.append(subscriberCount)

    axis.set_xticks(linearTickValues)
    axis.set_xlim(0.0, float(xLimit) * 1.03)
    axis.set_title("Encrypted Session Key over Subscribers", fontsize=12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Encrypted Session Key Bytes")
    axis.set_ylim(bottom=0.0)
    axis.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.18)
    axis.legend(fontsize=9, loc="upper left")


def PlotCrossover(summary: CrossoverSummary) -> None:

    bandwidthXLimit: int = int(summary.MeasuredSubscribers[-1])

    bandwidthFigure, bandwidthAxis = plt.subplots(figsize=(8.5, 5.2))

    DrawCrossoverPanel(
        bandwidthAxis,
        summary.MeasuredSubscribers,
        summary.MeasuredTotalBytes,
        summary.CpabeBytesMin,
        summary.CpabeBytesMax,
        summary.BytesCrossoverMin,
        summary.BytesCrossoverMax,
        bandwidthXLimit,
    )

    bandwidthFigure.tight_layout()
    plt.savefig(BANDWIDTH_CROSSOVER_PNG_FILE, dpi=150, bbox_inches="tight")
    plt.close(bandwidthFigure)
    print(f"Saved -> {BANDWIDTH_CROSSOVER_PNG_FILE}")


def PlotEncryptDecryptAsymmetry(results: dict[str, BenchmarkMetrics]) -> None:

    minAttributeCount: int = ATTRIBUTE_COUNTS[0]

    # Compare both schemes while they protect the same fixed-size session key.
    rsaEncryptMicros: float = GetMeanLatencyMicros(
        results, f"encrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}"
    )
    rsaDecryptMicros: float = GetMeanLatencyMicros(
        results, f"decrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}"
    )
    cpabeEncryptMicros: float = GetMeanLatencyMicros(
        results, f"encrypt/CPABEAttributes/{minAttributeCount}"
    )
    cpabeDecryptMicros: float = GetMeanLatencyMicros(
        results, f"decrypt/CPABEAttributes/{minAttributeCount}"
    )

    figure, axis = plt.subplots(figsize=(9, 5.5))

    schemeLabels: list[str] = [
        f"RSA-{FIXED_RSA_KEY_BITS}",
        f"CP-ABE ({FormatAttributeLabel(minAttributeCount)})",
    ]
    encryptValues: list[float] = [rsaEncryptMicros, cpabeEncryptMicros]
    decryptValues: list[float] = [rsaDecryptMicros, cpabeDecryptMicros]

    positions: list[float] = [0.0, 1.25]
    barWidth: float = 0.34

    encryptPositions: list[float] = []
    decryptPositions: list[float] = []

    for position in positions:
        encryptPositions.append(position - barWidth / 2.0)
        decryptPositions.append(position + barWidth / 2.0)

    axis.bar(
        encryptPositions,
        encryptValues,
        width=barWidth,
        color=ENCRYPT_COLOR,
        label="Encrypt",
    )
    axis.bar(
        decryptPositions,
        decryptValues,
        width=barWidth,
        color=DECRYPT_COLOR,
        label="Decrypt",
    )

    largestValue: float = max(max(encryptValues), max(decryptValues))

    for index in range(len(positions)):

        # Keep each value label a fixed visual distance above its bar.
        axis.annotate(
            f"{encryptValues[index]:,.1f} µs",
            (encryptPositions[index], encryptValues[index]),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=9,
        )
        axis.annotate(
            f"{decryptValues[index]:,.1f} µs",
            (decryptPositions[index], decryptValues[index]),
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
            fontsize=9,
        )

        if encryptValues[index] >= decryptValues[index]:
            ratioValue: float = encryptValues[index] / decryptValues[index]
            ratioText: str = f"Encrypt is {ratioValue:.0f}× Slower"
        else:
            ratioValue = decryptValues[index] / encryptValues[index]
            ratioText = f"Decrypt is {ratioValue:.0f}× Slower"

        tallestValue: float = max(encryptValues[index], decryptValues[index])
        ratioPosition: float = tallestValue + largestValue * 0.10

        axis.text(
            positions[index],
            ratioPosition,
            ratioText,
            ha="center",
            fontsize=10,
            fontweight="bold",
        )

    # A zero-based linear axis keeps bar heights proportional to the measured microseconds.
    axis.set_ylim(0.0, largestValue * 1.24)
    axis.set_xticks(positions)
    axis.set_xticklabels(schemeLabels)
    axis.set_ylabel("Latency (µs)")
    axis.set_title("Encrypt vs Decrypt Asymmetry", fontsize=12)
    axis.grid(False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    axis.legend(loc="upper center", ncol=2, frameon=False, fontsize=10)

    plt.tight_layout()
    plt.savefig(ASYMMETRY_PNG_FILE, dpi=150, bbox_inches="tight")
    print(f"Saved -> {ASYMMETRY_PNG_FILE}")


def BuildSweepOperationTable(
    results: dict[str, BenchmarkMetrics],
    sweepName: str,
    sweepValues: list[int],
    operation: str,
    valueHeader: str,
    includeSingleCiphertext: bool,
    includeTotalCiphertext: bool,
    includeStoredKey: bool,
) -> str:

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append(f"<th>{valueHeader.upper()}</th>")
    lines.append("<th>LATENCY (µs/op)</th>")

    if includeSingleCiphertext:
        lines.append("<th>CIPHERTEXT</th>")

    if includeTotalCiphertext:
        lines.append("<th>CIPHERTEXT (TOTAL)</th>")

    if includeStoredKey:
        lines.append("<th>STORED KEY</th>")

    lines.append(f"<th>ITERS (Σ{RUNS} RUNS)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    for sweepValue in sweepValues:

        benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"
        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
        if metrics is None:
            continue

        latencyMean: float
        latencyCI: float

        latencyMean, latencyCI = MeanAndConfidenceInterval(
            metrics.NsPerOperation,
            T_95,
        )

        singleCiphertextText: str = "—"
        if includeSingleCiphertext and len(metrics.SingleCiphertextBytes) > 0:
            singleCiphertextText = FormatByteSize(
                int(round(Mean(metrics.SingleCiphertextBytes)))
            )

        totalCiphertextText: str = "—"
        if includeTotalCiphertext and len(metrics.TotalCiphertextBytes) > 0:
            totalCiphertextText = FormatByteSize(
                int(round(Mean(metrics.TotalCiphertextBytes)))
            )

        storedKeyText: str = "—"
        if includeStoredKey and len(metrics.StoredKeyBytes) > 0:
            storedKeyText = FormatByteSize(int(round(Mean(metrics.StoredKeyBytes))))

        caseIterations: int = 0

        for iterationCount in metrics.Iterations:
            caseIterations += iterationCount

        # Convert Go's nanoseconds per operation to microseconds.
        latencyText: str = f"{latencyMean / 1000.0:.2f} ± {latencyCI / 1000.0:.2f}"

        lines.append("<tr>")
        lines.append(f"<td>{sweepValue}</td>")
        lines.append(f"<td>{latencyText}</td>")

        if includeSingleCiphertext:
            lines.append(f"<td>{singleCiphertextText}</td>")

        if includeTotalCiphertext:
            lines.append(f"<td>{totalCiphertextText}</td>")

        if includeStoredKey:
            lines.append(f"<td>{storedKeyText}</td>")

        lines.append(f"<td>{caseIterations:,}</td>")
        lines.append("</tr>")

    lines.append("</tbody>")
    lines.append("</table>")

    return "\n".join(lines)


def BuildRepeatedLatencyTable(
    results: dict[str, BenchmarkMetrics],
    sourceBenchmarkCaseId: str,
    sweepValues: list[int],
    valueHeader: str,
) -> str:

    metrics: BenchmarkMetrics | None = results.get(sourceBenchmarkCaseId)

    if metrics is None:
        sys.exit(
            f"[error] missing benchmark case '{sourceBenchmarkCaseId}' in {BENCH_FILE}"
        )

    latencyMean: float
    latencyCI: float
    latencyMean, latencyCI = MeanAndConfidenceInterval(
        metrics.NsPerOperation,
        T_95,
    )

    caseIterations: int = 0
    for iterationCount in metrics.Iterations:
        caseIterations += iterationCount

    latencyText: str = f"{latencyMean / 1000.0:.2f} ± {latencyCI / 1000.0:.2f}"

    lines: list[str] = []

    lines.append("<table>")
    lines.append("<thead>")
    lines.append("<tr>")
    lines.append(f"<th>{valueHeader.upper()}</th>")
    lines.append("<th>LATENCY (µs/op)</th>")
    lines.append(f"<th>ITERS (Σ{RUNS} RUNS)</th>")
    lines.append("</tr>")
    lines.append("</thead>")
    lines.append("<tbody>")

    # Repeat the fixed RSA decrypt measurement to show that audience size does not change it.
    for sweepValue in sweepValues:
        lines.append("<tr>")
        lines.append(f"<td>{sweepValue}</td>")
        lines.append(f"<td>{latencyText}</td>")
        lines.append(f"<td>{caseIterations:,}</td>")
        lines.append("</tr>")

    lines.append("</tbody>")
    lines.append("</table>")

    return "\n".join(lines)


def WriteHtmlReport(
    results: dict[str, BenchmarkMetrics],
    crossoverSummary: CrossoverSummary,
) -> None:

    totalIterations: int = 0

    for metrics in results.values():
        for iterationCount in metrics.Iterations:
            totalIterations += iterationCount

    cpabeEncryptTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "encrypt",
        "Attributes",
        True,
        False,
        False,
    )
    cpabeDecryptTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "decrypt",
        "Attributes",
        False,
        False,
        False,
    )
    cpabeKeygenTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "keygen",
        "Attributes",
        False,
        False,
        True,
    )
    rsaSubscribersEncryptTable: str = BuildSweepOperationTable(
        results,
        "RSASubscribers",
        SUBSCRIBER_COUNTS,
        "encrypt",
        "Subscribers",
        True,
        True,
        False,
    )
    rsaSubscribersDecryptTable: str = BuildRepeatedLatencyTable(
        results,
        f"decrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}",
        SUBSCRIBER_COUNTS,
        "Subscribers",
    )
    rsaKeyBitsEncryptTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "encrypt",
        "Key Bits",
        True,
        False,
        False,
    )
    rsaKeyBitsDecryptTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "decrypt",
        "Key Bits",
        False,
        False,
        False,
    )
    rsaKeyBitsKeygenTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "keygen",
        "Key Bits",
        False,
        False,
        True,
    )

    cpabeEncryptSlopeMicros: float
    cpabeCiphertextSlopeBytes: float
    cpabeStoredKeySlopeBytes: float
    cpabeEncryptSlopeMicros, cpabeCiphertextSlopeBytes, cpabeStoredKeySlopeBytes = (
        ComputeCpabeMarginalSlopes(results)
    )

    rsaEncryptSlopeMicros: float
    rsaTotalCiphertextSlopeBytes: float
    rsaDecryptSlopeMicros: float
    rsaEncryptSlopeMicros, rsaTotalCiphertextSlopeBytes, rsaDecryptSlopeMicros = (
        ComputeRsaSubscriberMarginalSlopes(results)
    )

    # Fan-out visual: the contrast is starkest at the largest subscriber count tested.
    maxSubscriberCount: int = SUBSCRIBER_COUNTS[-1]
    fanoutCaseId: str = f"encrypt/RSASubscribers/{maxSubscriberCount}"

    fanoutSingleBytes: float = GetMeanSingleCiphertextBytes(results, fanoutCaseId)
    fanoutTotalBytes: float = GetMeanTotalCiphertextBytes(results, fanoutCaseId)

    # Diameter scales with sqrt(bytes), so on-screen area tracks the byte count.
    fanoutSingleDiameterPx: float = max(
        FANOUT_SMALLEST_DIAMETER_PX,
        FANOUT_LARGEST_DIAMETER_PX * (fanoutSingleBytes / fanoutTotalBytes) ** 0.5,
    )

    bytesCrossoverLow: float = min(
        crossoverSummary.BytesCrossoverMin,
        crossoverSummary.BytesCrossoverMax,
    )
    bytesCrossoverHigh: float = max(
        crossoverSummary.BytesCrossoverMin,
        crossoverSummary.BytesCrossoverMax,
    )

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95))
    report = report.replace("{{DegreesOfFreedom}}", str(RUNS - 1))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")

    report = report.replace(
        "{{MinAttributeLabel}}", FormatAttributeLabel(ATTRIBUTE_COUNTS[0])
    )
    report = report.replace(
        "{{MaxAttributeLabel}}", FormatAttributeLabel(ATTRIBUTE_COUNTS[-1])
    )
    report = report.replace("{{MaxSubscriberCount}}", str(maxSubscriberCount))
    report = report.replace("{{FixedRsaKeyBits}}", str(FIXED_RSA_KEY_BITS))

    report = report.replace("{{CpabeEncryptTable}}", cpabeEncryptTable)
    report = report.replace("{{CpabeDecryptTable}}", cpabeDecryptTable)
    report = report.replace("{{CpabeKeygenTable}}", cpabeKeygenTable)
    report = report.replace(
        "{{RsaSubscribersEncryptTable}}", rsaSubscribersEncryptTable
    )
    report = report.replace(
        "{{RsaSubscribersDecryptTable}}", rsaSubscribersDecryptTable
    )
    report = report.replace("{{RsaKeyBitsEncryptTable}}", rsaKeyBitsEncryptTable)
    report = report.replace("{{RsaKeyBitsDecryptTable}}", rsaKeyBitsDecryptTable)
    report = report.replace("{{RsaKeyBitsKeygenTable}}", rsaKeyBitsKeygenTable)

    report = report.replace("{{CpabePlot}}", "cpabe_attributes.png")
    report = report.replace("{{RsaSubscribersPlot}}", "rsa_subscribers.png")
    report = report.replace("{{RsaKeyBitsPlot}}", "rsa_key_bits.png")
    report = report.replace("{{BandwidthCrossoverPlot}}", "bandwidth_crossover.png")
    report = report.replace("{{AsymmetryPlot}}", "encrypt_decrypt_asymmetry.png")

    report = report.replace(
        "{{CpabeEncryptSlope}}", f"+{cpabeEncryptSlopeMicros:,.0f} µs"
    )
    report = report.replace(
        "{{CpabeCiphertextSlope}}", f"+{cpabeCiphertextSlopeBytes:.0f} B"
    )
    report = report.replace(
        "{{CpabeStoredKeySlope}}", f"+{cpabeStoredKeySlopeBytes:.0f} B"
    )

    report = report.replace(
        "{{RsaSubscriberEncryptSlope}}", f"+{rsaEncryptSlopeMicros:,.2f} µs"
    )
    report = report.replace(
        "{{RsaSubscriberTotalCiphertextSlope}}",
        f"+{rsaTotalCiphertextSlopeBytes:.0f} B",
    )
    report = report.replace(
        "{{RsaSubscriberDecryptSlope}}", f"{rsaDecryptSlopeMicros:+.2f} µs"
    )

    report = report.replace(
        "{{FanoutSingleBytes}}", FormatByteSize(int(round(fanoutSingleBytes)))
    )
    report = report.replace(
        "{{FanoutTotalBytes}}", FormatByteSize(int(round(fanoutTotalBytes)))
    )
    report = report.replace(
        "{{FanoutMultiplier}}", f"{fanoutTotalBytes / fanoutSingleBytes:.0f}"
    )

    fanoutSingleStyle: str = (
        f'style="width:{fanoutSingleDiameterPx:.0f}px;'
        f'height:{fanoutSingleDiameterPx:.0f}px;"'
    )
    report = report.replace("{{FanoutSingleStyle}}", fanoutSingleStyle)

    fanoutTotalStyle: str = (
        f'style="width:{FANOUT_LARGEST_DIAMETER_PX:.0f}px;'
        f'height:{FANOUT_LARGEST_DIAMETER_PX:.0f}px;"'
    )
    report = report.replace("{{FanoutTotalStyle}}", fanoutTotalStyle)

    report = report.replace("{{BytesCrossoverLow}}", f"{bytesCrossoverLow:,.1f}")
    report = report.replace("{{BytesCrossoverHigh}}", f"{bytesCrossoverHigh:,.1f}")
    report = report.replace(
        "{{BytesCrossoverMin}}", f"{crossoverSummary.BytesCrossoverMin:,.1f}"
    )
    report = report.replace(
        "{{BytesCrossoverMax}}", f"{crossoverSummary.BytesCrossoverMax:,.1f}"
    )
    report = report.replace(
        "{{BytesRsaThroughMin}}",
        f"{max(0, int(crossoverSummary.BytesCrossoverMin)):,}",
    )
    report = report.replace(
        "{{BytesCpabeFromMin}}",
        f"{int(crossoverSummary.BytesCrossoverMin) + 1:,}",
    )
    report = report.replace(
        "{{BytesRsaThroughMax}}",
        f"{max(0, int(crossoverSummary.BytesCrossoverMax)):,}",
    )
    report = report.replace(
        "{{BytesCpabeFromMax}}",
        f"{int(crossoverSummary.BytesCrossoverMax) + 1:,}",
    )

    with open(HTML_FILE, "w", encoding="utf-8") as file:
        file.write(report)

    print(f"Saved -> {HTML_FILE}")


def Main() -> None:

    try:
        results: dict[str, BenchmarkMetrics] = ParseBenchmarkFile(BENCH_FILE)
    except FileNotFoundError:
        sys.exit(f"[error] {BENCH_FILE} not found — run the benchmark first")

    PlotSweep(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        OPERATIONS,
        "Policy Attributes",
        "CP-ABE Scaling with Policy Attribute Count",
        CPABE_PNG_FILE,
    )

    # Decrypt is passed as a constant rather than a swept series, because it does not vary with
    # audience size. Keygen is absent because the key size is fixed across this sweep.
    PlotSweep(
        results,
        "RSASubscribers",
        SUBSCRIBER_COUNTS,
        ["encrypt"],
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {FIXED_RSA_KEY_BITS} bits)",
        RSA_SUBSCRIBERS_PNG_FILE,
        GetMeanLatencyMicros(results, f"decrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}"),
    )

    PlotSweep(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        OPERATIONS,
        "RSA Key Bits",
        "RSA Scaling with Key Size (1 Subscriber)",
        RSA_KEY_BITS_PNG_FILE,
    )

    # Compute the measured bandwidth crossover used by the plot and explanation.
    crossoverSummary: CrossoverSummary = ComputeCrossoverSummary(results)

    PlotCrossover(crossoverSummary)
    PlotEncryptDecryptAsymmetry(results)

    WriteHtmlReport(results, crossoverSummary)


if __name__ == "__main__":
    Main()
