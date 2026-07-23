import matplotlib

matplotlib.use("Agg")

import sys
import matplotlib.pyplot as plt
from utils.statistics import GetStudentTCriticalValue95
from utils.statistics import Mean
from utils.statistics import MeanAndConfidenceInterval
from utils.statistics import FitLinearRegression
from utils.statistics import FitPowerLaw
from utils.statistics import ComputeSlopeConfidenceInterval
from utils.parser import ParseIntListFromEnv
from utils.parser import ParseIntFromEnv
from utils.formatter import FormatByteSize

BENCH_FILE: str = "/results/attribute-key-scaling/bench_output.txt"
CPABE_PNG_FILE: str = "/results/attribute-key-scaling/cpabe_attributes.png"
RSA_SUBSCRIBERS_PNG_FILE: str = "/results/attribute-key-scaling/rsa_subscribers.png"
RSA_KEY_BITS_PNG_FILE: str = "/results/attribute-key-scaling/rsa_key_bits.png"
BANDWIDTH_CROSSOVER_PNG_FILE: str = (
    "/results/attribute-key-scaling/bandwidth_crossover.png"
)
ASYMMETRY_PNG_FILE: str = "/results/attribute-key-scaling/encrypt_decrypt_asymmetry.png"
ENCRYPT_CPU_CROSSOVER_PNG_FILE: str = (
    "/results/attribute-key-scaling/encrypt_cpu_crossover.png"
)
DECRYPT_CPU_CROSSOVER_PNG_FILE: str = (
    "/results/attribute-key-scaling/decrypt_cpu_crossover.png"
)
HTML_FILE: str = "/results/attribute-key-scaling/report.html"
HTML_TEMPLATE_FILE: str = "/app/template/attribute_key_scaling_template.html"

RUNS: int = ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_RUNS")
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
FIXED_RSA_KEY_BITS: int = ParseIntFromEnv("ATTRIBUTE_KEY_SCALING_FIXED_RSA_KEY_BITS")
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

    def __init__(self) -> None:

        self.Iterations: list[int] = []
        self.NsPerOperation: list[float] = []
        self.SingleCiphertextBytes: list[float] = []
        self.TotalCiphertextBytes: list[float] = []
        self.StoredKeyBytes: list[float] = []


class CrossoverSummary:

    def __init__(self) -> None:

        # RSA fan-out bytes measured across the subscriber sweep.
        self.MeasuredTotalBytes: list[float] = []

        # CP-ABE ciphertext sizes at the smallest and largest tested policies.
        self.CpabeBytesMin: float = 0.0
        self.CpabeBytesMax: float = 0.0

        # Audience sizes where measured byte-growth relationships are equal.
        self.BytesCrossoverMin: float = 0.0
        self.BytesCrossoverMax: float = 0.0


class CpuCrossoverSummary:

    def __init__(self) -> None:

        # Publisher encrypt cost measured across the RSA subscriber sweep.
        self.MeasuredEncryptMicros: list[float] = []

        # Cost RSA adds for one more recipient, taken at the smallest audience tested.
        self.RsaEncryptPerSubscriberMicros: float = 0.0

        # Audience-independent RSA private-key cost at the fixed key size.
        self.RsaDecryptMicros: float = 0.0

        # CP-ABE costs at the smallest and largest tested policies.
        self.CpabeEncryptMicrosMin: float = 0.0
        self.CpabeEncryptMicrosMax: float = 0.0
        self.CpabeDecryptMicrosMin: float = 0.0
        self.CpabeDecryptMicrosMax: float = 0.0

        # Audience sizes where publisher CPU cost is equal.
        self.EncryptCrossoverMin: float = 0.0
        self.EncryptCrossoverMax: float = 0.0

        # How much more subscriber CPU CP-ABE costs, at every audience size.
        self.DecryptPenaltyMin: float = 0.0
        self.DecryptPenaltyMax: float = 0.0


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
            nameParts: list[str] = benchmarkName[len(prefix) :].split("/")
            operation: str = nameParts[0].lower()
            sweepName: str = nameParts[1]
            sweepValueText: str = nameParts[2]

            # Strip the GOMAXPROCS suffix (e.g. "-1"); the sweep value carries no unit label.
            sweepValue: int = int(sweepValueText.split("-")[0])

            benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"

            if benchmarkCaseId not in results:
                results[benchmarkCaseId] = BenchmarkMetrics()

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


def GetMeanStoredKeyBytes(
    results: dict[str, BenchmarkMetrics],
    benchmarkCaseId: str,
) -> float:

    metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

    if metrics is None or len(metrics.StoredKeyBytes) == 0:
        sys.exit(
            f"[error] missing stored key bytes for '{benchmarkCaseId}' in {BENCH_FILE}"
        )

    return Mean(metrics.StoredKeyBytes)


def PlotSweep(
    results: dict[str, BenchmarkMetrics],
    sweepName: str,
    sweepValues: list[int],
    sweepOperations: list[str],
    derivedStoredKeySizes: list[float],
    xLabel: str,
    figureTitle: str,
    pngFile: str,
    fixedDecryptCaseId: str | None = None,
) -> None:

    figure, axes = plt.subplots(1, 2, figsize=(13, 5))

    figure.suptitle(figureTitle, fontsize=13)

    latencyAxis = axes[0]
    sizeAxis = axes[1]

    latencyMean: float
    latencyCI: float

    # Left panel: latency per operation across the sweep.
    for operation in sweepOperations:

        means: list[float] = []
        ciHalfs: list[float] = []
        values: list[int] = []

        for sweepValue in sweepValues:

            benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"

            # Reuse one measured fixed-key decrypt result across the subscriber axis.
            if operation == "decrypt" and fixedDecryptCaseId is not None:
                benchmarkCaseId = fixedDecryptCaseId

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

    latencyAxis.set_title("Latency", fontsize=11)
    latencyAxis.set_ylabel("Latency (µs) ± 95% CI")
    latencyAxis.set_ylim(bottom=0)
    # Real numerical spacing, so horizontal distance represents the actual sweep increase.
    latencyAxis.set_xticks(sweepValues)
    latencyAxis.set_xlabel(xLabel)
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

    if len(derivedStoredKeySizes) > 0:
        storedKeyValues = list(sweepValues)
        storedKeySizes = derivedStoredKeySizes

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
        )

    # The keygen sweep does not run for every case, so this series may be absent.
    if len(storedKeyValues) > 0:
        sizeAxis.plot(
            storedKeyValues,
            storedKeySizes,
            label="Private Key",
            color=KEYGEN_COLOR,
            marker="o",
            linewidth=1.8,
            markersize=5,
        )

    sizeAxis.set_title("Sizes", fontsize=11)
    sizeAxis.set_ylabel("Size (bytes)")
    # Explicit sweep ticks on a linear axis, so a straight line here IS linear growth.
    sizeAxis.set_xticks(sweepValues)
    sizeAxis.set_xlabel(xLabel)
    sizeAxis.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.18)
    sizeAxis.legend(fontsize=10)
    # Anchor at zero so proportions between the series are honest.
    sizeAxis.set_ylim(bottom=0)

    figure.tight_layout(rect=[0.0, 0.0, 1.0, 0.94])  # type: ignore
    figure.savefig(pngFile, dpi=150, bbox_inches="tight")
    plt.close(figure)
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

        summary.MeasuredTotalBytes.append(Mean(metrics.TotalCiphertextBytes))

    # Bytes of a single wrapped session key, the unit RSA adds per extra subscriber.
    rsaSingleBytes: float = GetMeanSingleCiphertextBytes(
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
    summary.BytesCrossoverMin = summary.CpabeBytesMin / rsaSingleBytes
    summary.BytesCrossoverMax = summary.CpabeBytesMax / rsaSingleBytes

    return summary


def ComputeCpuCrossoverSummary(
    results: dict[str, BenchmarkMetrics],
) -> CpuCrossoverSummary:

    summary: CpuCrossoverSummary = CpuCrossoverSummary()

    minAttributeCount: int = ATTRIBUTE_COUNTS[0]
    maxAttributeCount: int = ATTRIBUTE_COUNTS[-1]

    for subscriberCount in SUBSCRIBER_COUNTS:

        summary.MeasuredEncryptMicros.append(
            GetMeanLatencyMicros(
                results,
                f"encrypt/RSASubscribers/{subscriberCount}",
            )
        )

    # One RSA encryption is repeated once for every recipient.
    summary.RsaEncryptPerSubscriberMicros = GetMeanLatencyMicros(
        results,
        f"encrypt/RSASubscribers/{SUBSCRIBER_COUNTS[0]}",
    )

    # RSA decrypt scaling is taken from the measured key-size sweep.
    summary.RsaDecryptMicros = GetMeanLatencyMicros(
        results,
        f"decrypt/RSAKeyBits/{FIXED_RSA_KEY_BITS}",
    )

    summary.CpabeEncryptMicrosMin = GetMeanLatencyMicros(
        results,
        f"encrypt/CPABEAttributes/{minAttributeCount}",
    )
    summary.CpabeEncryptMicrosMax = GetMeanLatencyMicros(
        results,
        f"encrypt/CPABEAttributes/{maxAttributeCount}",
    )
    summary.CpabeDecryptMicrosMin = GetMeanLatencyMicros(
        results,
        f"decrypt/CPABEAttributes/{minAttributeCount}",
    )
    summary.CpabeDecryptMicrosMax = GetMeanLatencyMicros(
        results,
        f"decrypt/CPABEAttributes/{maxAttributeCount}",
    )

    summary.EncryptCrossoverMin = (
        summary.CpabeEncryptMicrosMin / summary.RsaEncryptPerSubscriberMicros
    )
    summary.EncryptCrossoverMax = (
        summary.CpabeEncryptMicrosMax / summary.RsaEncryptPerSubscriberMicros
    )

    summary.DecryptPenaltyMin = summary.CpabeDecryptMicrosMin / summary.RsaDecryptMicros
    summary.DecryptPenaltyMax = summary.CpabeDecryptMicrosMax / summary.RsaDecryptMicros

    return summary


def ComputeCpabeMarginalSlopes(
    results: dict[str, BenchmarkMetrics],
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]:

    encryptAttributeValues: list[float] = []
    encryptMicrosValues: list[float] = []
    decryptAttributeValues: list[float] = []
    decryptMicrosValues: list[float] = []
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

        # Fitted separately from encrypt, because publisher and subscriber pay different marginal costs.
        decryptMetrics: BenchmarkMetrics | None = results.get(
            f"decrypt/CPABEAttributes/{attributeCount}"
        )
        if decryptMetrics is not None and len(decryptMetrics.NsPerOperation) > 0:
            decryptAttributeValues.append(float(attributeCount))
            decryptMicrosValues.append(Mean(decryptMetrics.NsPerOperation) / 1000.0)

        keygenMetrics: BenchmarkMetrics | None = results.get(
            f"keygen/CPABEAttributes/{attributeCount}"
        )
        if keygenMetrics is not None and len(keygenMetrics.StoredKeyBytes) > 0:
            storedKeyAttributeValues.append(float(attributeCount))
            storedKeyBytesValues.append(Mean(keygenMetrics.StoredKeyBytes))

    encryptSlopeMicros: float
    encryptRSquared: float
    encryptSlopeStandardError: float
    encryptSlopeMicros, encryptRSquared, encryptSlopeStandardError = (
        FitLinearRegression(encryptAttributeValues, encryptMicrosValues)
    )
    encryptSlopeCI: float = ComputeSlopeConfidenceInterval(
        encryptSlopeStandardError, len(encryptAttributeValues)
    )

    decryptSlopeMicros: float
    decryptRSquared: float
    decryptSlopeStandardError: float
    decryptSlopeMicros, decryptRSquared, decryptSlopeStandardError = (
        FitLinearRegression(decryptAttributeValues, decryptMicrosValues)
    )
    decryptSlopeCI: float = ComputeSlopeConfidenceInterval(
        decryptSlopeStandardError, len(decryptAttributeValues)
    )

    ciphertextSlopeBytes: float
    ciphertextRSquared: float
    ciphertextSlopeStandardError: float
    ciphertextSlopeBytes, ciphertextRSquared, ciphertextSlopeStandardError = (
        FitLinearRegression(ciphertextAttributeValues, ciphertextBytesValues)
    )
    ciphertextSlopeCI: float = ComputeSlopeConfidenceInterval(
        ciphertextSlopeStandardError, len(ciphertextAttributeValues)
    )

    storedKeySlopeBytes: float
    storedKeyRSquared: float
    storedKeySlopeStandardError: float
    storedKeySlopeBytes, storedKeyRSquared, storedKeySlopeStandardError = (
        FitLinearRegression(storedKeyAttributeValues, storedKeyBytesValues)
    )
    storedKeySlopeCI: float = ComputeSlopeConfidenceInterval(
        storedKeySlopeStandardError, len(storedKeyAttributeValues)
    )

    return (
        encryptSlopeMicros,
        decryptSlopeMicros,
        ciphertextSlopeBytes,
        storedKeySlopeBytes,
        encryptRSquared,
        decryptRSquared,
        ciphertextRSquared,
        storedKeyRSquared,
        encryptSlopeCI,
        decryptSlopeCI,
        ciphertextSlopeCI,
        storedKeySlopeCI,
    )


def ComputeRsaSubscriberMarginalSlopes(
    results: dict[str, BenchmarkMetrics],
) -> tuple[float, float, float, float]:

    subscriberValues: list[float] = []
    encryptMicrosValues: list[float] = []

    for subscriberCount in SUBSCRIBER_COUNTS:

        encryptMetrics: BenchmarkMetrics | None = results.get(
            f"encrypt/RSASubscribers/{subscriberCount}"
        )

        if encryptMetrics is None:
            continue

        subscriberValues.append(float(subscriberCount))
        encryptMicrosValues.append(Mean(encryptMetrics.NsPerOperation) / 1000.0)

    encryptSlopeMicros: float
    encryptRSquared: float
    encryptSlopeStandardError: float

    (
        encryptSlopeMicros,
        encryptRSquared,
        encryptSlopeStandardError,
    ) = FitLinearRegression(
        subscriberValues,
        encryptMicrosValues,
    )

    encryptSlopeCI: float = ComputeSlopeConfidenceInterval(
        encryptSlopeStandardError,
        len(subscriberValues),
    )

    # RSA adds one independently wrapped key for each additional subscriber.
    totalCiphertextSlopeBytes: float = GetMeanSingleCiphertextBytes(
        results,
        f"encrypt/RSASubscribers/{SUBSCRIBER_COUNTS[0]}",
    )

    return (
        encryptSlopeMicros,
        totalCiphertextSlopeBytes,
        encryptRSquared,
        encryptSlopeCI,
    )


def ComputeRsaKeyBitsMarginalSlopes(
    results: dict[str, BenchmarkMetrics],
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
    float,
]:

    keyBitsValues: list[float] = []
    encryptMicrosValues: list[float] = []
    decryptMicrosValues: list[float] = []
    keygenMicrosValues: list[float] = []
    ciphertextBytesValues: list[float] = []
    storedKeyBytesValues: list[float] = []

    for rsaKeyBits in RSA_KEY_BITS_LIST:

        encryptMetrics: BenchmarkMetrics | None = results.get(
            f"encrypt/RSAKeyBits/{rsaKeyBits}"
        )
        decryptMetrics: BenchmarkMetrics | None = results.get(
            f"decrypt/RSAKeyBits/{rsaKeyBits}"
        )
        keygenMetrics: BenchmarkMetrics | None = results.get(
            f"keygen/RSAKeyBits/{rsaKeyBits}"
        )

        if encryptMetrics is None or decryptMetrics is None or keygenMetrics is None:
            continue

        keyBitsValues.append(float(rsaKeyBits))
        encryptMicrosValues.append(Mean(encryptMetrics.NsPerOperation) / 1000.0)
        decryptMicrosValues.append(Mean(decryptMetrics.NsPerOperation) / 1000.0)
        keygenMicrosValues.append(Mean(keygenMetrics.NsPerOperation) / 1000.0)
        ciphertextBytesValues.append(Mean(encryptMetrics.SingleCiphertextBytes))
        storedKeyBytesValues.append(Mean(keygenMetrics.StoredKeyBytes))

    # Modular arithmetic cost is polynomial in modulus width, so a straight line is the wrong model.
    encryptExponent: float
    encryptRSquared: float
    encryptExponentStandardError: float
    encryptExponent, encryptRSquared, encryptExponentStandardError = FitPowerLaw(
        keyBitsValues, encryptMicrosValues
    )
    encryptExponentCI: float = ComputeSlopeConfidenceInterval(
        encryptExponentStandardError, len(keyBitsValues)
    )

    decryptExponent: float
    decryptRSquared: float
    decryptExponentStandardError: float
    decryptExponent, decryptRSquared, decryptExponentStandardError = FitPowerLaw(
        keyBitsValues, decryptMicrosValues
    )
    decryptExponentCI: float = ComputeSlopeConfidenceInterval(
        decryptExponentStandardError, len(keyBitsValues)
    )

    keygenExponent: float
    keygenRSquared: float
    keygenExponentStandardError: float
    keygenExponent, keygenRSquared, keygenExponentStandardError = FitPowerLaw(
        keyBitsValues, keygenMicrosValues
    )
    keygenExponentCI: float = ComputeSlopeConfidenceInterval(
        keygenExponentStandardError, len(keyBitsValues)
    )

    # Both sizes are plain byte counts derived from the modulus, so these really are linear.
    ciphertextSlopeBytes: float
    ciphertextRSquared: float
    ciphertextSlopeStandardError: float
    ciphertextSlopeBytes, ciphertextRSquared, ciphertextSlopeStandardError = (
        FitLinearRegression(keyBitsValues, ciphertextBytesValues)
    )
    ciphertextSlopeCI: float = ComputeSlopeConfidenceInterval(
        ciphertextSlopeStandardError, len(keyBitsValues)
    )

    storedKeySlopeBytes: float
    storedKeyRSquared: float
    storedKeySlopeStandardError: float
    storedKeySlopeBytes, storedKeyRSquared, storedKeySlopeStandardError = (
        FitLinearRegression(keyBitsValues, storedKeyBytesValues)
    )
    storedKeySlopeCI: float = ComputeSlopeConfidenceInterval(
        storedKeySlopeStandardError, len(keyBitsValues)
    )

    return (
        encryptExponent,
        decryptExponent,
        keygenExponent,
        ciphertextSlopeBytes,
        storedKeySlopeBytes,
        encryptRSquared,
        decryptRSquared,
        keygenRSquared,
        ciphertextRSquared,
        storedKeyRSquared,
        encryptExponentCI,
        decryptExponentCI,
        keygenExponentCI,
        ciphertextSlopeCI,
        storedKeySlopeCI,
    )


def PlotCrossover(summary: CrossoverSummary) -> None:

    xLimit: int = SUBSCRIBER_COUNTS[-1]

    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    # Plot only values observed in the RSA subscriber sweep.
    axis.plot(
        SUBSCRIBER_COUNTS,
        summary.MeasuredTotalBytes,
        color=TOTAL_CIPHERTEXT_COLOR,
        marker="^",
        linewidth=1.8,
        markersize=5,
        label="RSA Scaling Subs",
    )

    # One CP-ABE ciphertext serves the complete subscriber audience.
    axis.hlines(
        summary.CpabeBytesMin,
        1,
        xLimit,
        color=ENCRYPT_COLOR,
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[0])}",
    )
    axis.hlines(
        summary.CpabeBytesMax,
        1,
        xLimit,
        color=KEYGEN_COLOR,
        linestyle="-.",
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[-1])}",
    )

    # Mark the subscriber counts where the byte totals are equal.
    for crossoverValue, levelValue in (
        (summary.BytesCrossoverMin, summary.CpabeBytesMin),
        (summary.BytesCrossoverMax, summary.CpabeBytesMax),
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

    figure.tight_layout()
    figure.savefig(BANDWIDTH_CROSSOVER_PNG_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {BANDWIDTH_CROSSOVER_PNG_FILE}")


def PlotEncryptCpuCrossover(summary: CpuCrossoverSummary) -> None:

    # Extend past the furthest intersection so both crossings land on the axis.
    xLimit: float = summary.EncryptCrossoverMax * 1.15

    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    # RSA repeats one wrap per recipient, so publisher cost is per-recipient cost times audience.
    axis.plot(
        [0.0, xLimit],
        [0.0, summary.RsaEncryptPerSubscriberMicros * xLimit],
        color=TOTAL_CIPHERTEXT_COLOR,
        linewidth=1.8,
        linestyle=":",
        label="RSA Scaling Subs (Projected)",
    )

    # The measured portion of that same line, drawn heavier so it is distinguishable.
    axis.plot(
        SUBSCRIBER_COUNTS,
        summary.MeasuredEncryptMicros,
        color=TOTAL_CIPHERTEXT_COLOR,
        marker="^",
        linewidth=2.6,
        markersize=5,
        label="RSA Scaling Subs (Measured)",
    )

    # One CP-ABE encryption serves the complete subscriber audience.
    axis.hlines(
        summary.CpabeEncryptMicrosMin,
        0.0,
        xLimit,
        color=ENCRYPT_COLOR,
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[0])}",
    )
    axis.hlines(
        summary.CpabeEncryptMicrosMax,
        0.0,
        xLimit,
        color=KEYGEN_COLOR,
        linestyle="-.",
        linewidth=1.8,
        label=f"CP-ABE, {FormatAttributeLabel(ATTRIBUTE_COUNTS[-1])}",
    )

    # Mark the audience sizes where publisher CPU cost is equal.
    for crossoverValue, levelValue in (
        (summary.EncryptCrossoverMin, summary.CpabeEncryptMicrosMin),
        (summary.EncryptCrossoverMax, summary.CpabeEncryptMicrosMax),
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
            f"≈{crossoverValue:,.0f}",
            (crossoverValue, levelValue),
            textcoords="offset points",
            xytext=(6, 8),
            fontsize=9,
            fontweight="bold",
        )

    largestValue: float = max(
        summary.CpabeEncryptMicrosMax,
        summary.RsaEncryptPerSubscriberMicros * xLimit,
    )

    axis.set_xlim(0.0, xLimit)
    # Zero-based linear axis, so vertical distance is proportional to measured microseconds.
    axis.set_ylim(0.0, largestValue * 1.12)
    axis.set_title("Publisher Encrypt Cost over Subscribers", fontsize=12)
    axis.set_xlabel("Subscribers")
    axis.set_ylabel("Publisher Encrypt Latency (µs)")
    axis.grid(True, axis="y", linestyle="-", linewidth=0.5, alpha=0.18)
    axis.legend(fontsize=9, loc="upper left")

    figure.tight_layout()
    figure.savefig(ENCRYPT_CPU_CROSSOVER_PNG_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)
    print(f"Saved -> {ENCRYPT_CPU_CROSSOVER_PNG_FILE}")


def PlotDecryptCpuCrossover(
    results: dict[str, BenchmarkMetrics],
) -> None:

    figure, axis = plt.subplots(figsize=(8.5, 5.2))

    cpabeMeans: list[float] = []
    cpabeCiHalfs: list[float] = []
    largestValue: float = 0.0

    for attributeCount in ATTRIBUTE_COUNTS:

        benchmarkCaseId: str = f"decrypt/CPABEAttributes/{attributeCount}"

        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)

        if metrics is None:
            sys.exit(
                f"[error] missing benchmark case "
                f"'{benchmarkCaseId}' in {BENCH_FILE}"
            )

        latencyMean: float
        latencyCI: float

        latencyMean, latencyCI = MeanAndConfidenceInterval(
            metrics.NsPerOperation,
            T_95,
        )

        meanMicros: float = latencyMean / 1000.0
        ciMicros: float = latencyCI / 1000.0

        cpabeMeans.append(meanMicros)
        cpabeCiHalfs.append(ciMicros)

        largestValue = max(
            largestValue,
            meanMicros + ciMicros,
        )

    # Plot the measured CP-ABE decrypt scaling across policy attributes.
    axis.errorbar(
        ATTRIBUTE_COUNTS,
        cpabeMeans,
        yerr=cpabeCiHalfs,
        label="CP-ABE",
        color=DECRYPT_COLOR,
        marker="o",
        linewidth=2.0,
        markersize=5,
        capsize=4,
    )

    rsaColors: list[str] = [
        TOTAL_CIPHERTEXT_COLOR,
        "#2563eb",
        ENCRYPT_COLOR,
        KEYGEN_COLOR,
    ]

    for index in range(len(RSA_KEY_BITS_LIST)):

        rsaKeyBits: int = RSA_KEY_BITS_LIST[index]

        benchmarkCaseId = f"decrypt/RSAKeyBits/{rsaKeyBits}"

        metrics = results.get(benchmarkCaseId)

        if metrics is None:
            sys.exit(
                f"[error] missing benchmark case "
                f"'{benchmarkCaseId}' in {BENCH_FILE}"
            )

        latencyMean, latencyCI = MeanAndConfidenceInterval(
            metrics.NsPerOperation,
            T_95,
        )

        rsaMeanMicros: float = latencyMean / 1000.0
        rsaCiMicros: float = latencyCI / 1000.0
        rsaColor: str = rsaColors[index % len(rsaColors)]

        # Each RSA line represents one measured key size across the policy axis.
        axis.hlines(
            rsaMeanMicros,
            ATTRIBUTE_COUNTS[0],
            ATTRIBUTE_COUNTS[-1],
            color=rsaColor,
            linestyle="--",
            linewidth=1.6,
            label=f"RSA-{rsaKeyBits}",
        )

        # Show the measured RSA confidence interval at the end of its line.
        axis.errorbar(
            [ATTRIBUTE_COUNTS[-1]],
            [rsaMeanMicros],
            yerr=[rsaCiMicros],
            color=rsaColor,
            fmt="none",
            capsize=4,
        )

        largestValue = max(
            largestValue,
            rsaMeanMicros + rsaCiMicros,
        )

    axis.set_xticks(ATTRIBUTE_COUNTS)
    axis.set_xlim(
        0.0,
        float(ATTRIBUTE_COUNTS[-1]) * 1.03,
    )
    axis.set_ylim(
        0.0,
        largestValue * 1.15,
    )
    axis.set_title(
        "Subscriber Decrypt Cost over Policy Attributes",
        fontsize=12,
    )
    axis.set_xlabel("Policy Attributes")
    axis.set_ylabel("Decrypt Latency (µs) ± 95% CI")
    axis.grid(
        True,
        axis="y",
        linestyle="-",
        linewidth=0.5,
        alpha=0.18,
    )
    axis.legend(
        fontsize=9,
        loc="upper left",
    )

    figure.tight_layout()
    figure.savefig(
        DECRYPT_CPU_CROSSOVER_PNG_FILE,
        dpi=150,
        bbox_inches="tight",
    )
    plt.close(figure)

    print(f"Saved -> {DECRYPT_CPU_CROSSOVER_PNG_FILE}")


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

    figure.tight_layout()
    figure.savefig(ASYMMETRY_PNG_FILE, dpi=150, bbox_inches="tight")
    plt.close(figure)
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
    fixedBenchmarkCaseId: str | None = None,
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

    latencyMean: float
    latencyCI: float

    for sweepValue in sweepValues:

        benchmarkCaseId: str = f"{operation}/{sweepName}/{sweepValue}"

        # Display one measured fixed-key result for every subscriber count.
        if fixedBenchmarkCaseId is not None:
            benchmarkCaseId = fixedBenchmarkCaseId

        metrics: BenchmarkMetrics | None = results.get(benchmarkCaseId)
        if metrics is None:
            continue

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

        caseIterations: int = sum(metrics.Iterations)

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


def WriteHtmlReport(
    results: dict[str, BenchmarkMetrics],
    crossoverSummary: CrossoverSummary,
    cpuCrossoverSummary: CpuCrossoverSummary,
) -> None:

    totalIterations: int = 0

    for metrics in results.values():
        totalIterations += sum(metrics.Iterations)

    cpabeEncryptTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "encrypt",
        "Attributes",
        includeSingleCiphertext=True,
        includeTotalCiphertext=False,
        includeStoredKey=False,
    )
    cpabeDecryptTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "decrypt",
        "Attributes",
        includeSingleCiphertext=False,
        includeTotalCiphertext=False,
        includeStoredKey=False,
    )
    cpabeKeygenTable: str = BuildSweepOperationTable(
        results,
        "CPABEAttributes",
        ATTRIBUTE_COUNTS,
        "keygen",
        "Attributes",
        includeSingleCiphertext=False,
        includeTotalCiphertext=False,
        includeStoredKey=True,
    )
    rsaSubscribersEncryptTable: str = BuildSweepOperationTable(
        results,
        "RSASubscribers",
        SUBSCRIBER_COUNTS,
        "encrypt",
        "Subscribers",
        includeSingleCiphertext=True,
        includeTotalCiphertext=True,
        includeStoredKey=False,
    )
    rsaSubscribersDecryptTable: str = BuildSweepOperationTable(
        results,
        "RSASubscribers",
        SUBSCRIBER_COUNTS,
        "decrypt",
        "Subscribers",
        includeSingleCiphertext=False,
        includeTotalCiphertext=False,
        includeStoredKey=False,
        fixedBenchmarkCaseId=(f"decrypt/RSASubscriberFixedKey/{FIXED_RSA_KEY_BITS}"),
    )
    rsaKeyBitsEncryptTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "encrypt",
        "Key Bits",
        includeSingleCiphertext=True,
        includeTotalCiphertext=False,
        includeStoredKey=False,
    )
    rsaKeyBitsDecryptTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "decrypt",
        "Key Bits",
        includeSingleCiphertext=False,
        includeTotalCiphertext=False,
        includeStoredKey=False,
    )
    rsaKeyBitsKeygenTable: str = BuildSweepOperationTable(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        "keygen",
        "Key Bits",
        includeSingleCiphertext=False,
        includeTotalCiphertext=False,
        includeStoredKey=True,
    )

    (
        cpabeEncryptSlopeMicros,
        cpabeDecryptSlopeMicros,
        cpabeCiphertextSlopeBytes,
        cpabeStoredKeySlopeBytes,
        cpabeEncryptRSquared,
        cpabeDecryptRSquared,
        cpabeCiphertextRSquared,
        cpabeStoredKeyRSquared,
        cpabeEncryptSlopeCI,
        cpabeDecryptSlopeCI,
        cpabeCiphertextSlopeCI,
        cpabeStoredKeySlopeCI,
    ) = ComputeCpabeMarginalSlopes(results)

    (
        rsaEncryptSlopeMicros,
        rsaTotalCiphertextSlopeBytes,
        rsaEncryptRSquared,
        rsaEncryptSlopeCI,
    ) = ComputeRsaSubscriberMarginalSlopes(results)

    (
        rsaKeyBitsEncryptExponent,
        rsaKeyBitsDecryptExponent,
        rsaKeyBitsKeygenExponent,
        rsaKeyBitsCiphertextSlopeBytes,
        rsaKeyBitsStoredKeySlopeBytes,
        rsaKeyBitsEncryptRSquared,
        rsaKeyBitsDecryptRSquared,
        rsaKeyBitsKeygenRSquared,
        rsaKeyBitsCiphertextRSquared,
        rsaKeyBitsStoredKeyRSquared,
        rsaKeyBitsEncryptExponentCI,
        rsaKeyBitsDecryptExponentCI,
        rsaKeyBitsKeygenExponentCI,
        rsaKeyBitsCiphertextSlopeCI,
        rsaKeyBitsStoredKeySlopeCI,
    ) = ComputeRsaKeyBitsMarginalSlopes(results)

    # How much further out the CPU intersection sits than the bandwidth one.
    cpuGapMin: float = (
        cpuCrossoverSummary.EncryptCrossoverMin / crossoverSummary.BytesCrossoverMin
    )
    cpuGapMax: float = (
        cpuCrossoverSummary.EncryptCrossoverMax / crossoverSummary.BytesCrossoverMax
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

    with open(HTML_TEMPLATE_FILE, "r", encoding="utf-8") as file:
        template: str = file.read()

    report: str = template

    report = report.replace("{{RunCount}}", str(RUNS))
    report = report.replace("{{ConfidenceLevel}}", "95%")
    report = report.replace("{{TMultiplier}}", str(T_95))
    report = report.replace("{{TotalIterations}}", f"{totalIterations:,}")

    report = report.replace(
        "{{MinAttributeLabel}}", FormatAttributeLabel(ATTRIBUTE_COUNTS[0])
    )
    report = report.replace(
        "{{MaxAttributeLabel}}", FormatAttributeLabel(ATTRIBUTE_COUNTS[-1])
    )
    report = report.replace("{{MaxSubscriberCount}}", str(maxSubscriberCount))
    report = report.replace("{{FixedRsaKeyBits}}", str(FIXED_RSA_KEY_BITS))
    report = report.replace(
        "{{MinRsaKeyBits}}",
        str(RSA_KEY_BITS_LIST[0]),
    )
    report = report.replace(
        "{{MaxRsaKeyBits}}",
        str(RSA_KEY_BITS_LIST[-1]),
    )
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
    report = report.replace("{{EncryptCpuCrossoverPlot}}", "encrypt_cpu_crossover.png")
    report = report.replace("{{DecryptCpuCrossoverPlot}}", "decrypt_cpu_crossover.png")

    report = report.replace(
        "{{CpabeEncryptSlope}}",
        f"+{cpabeEncryptSlopeMicros:,.0f} ± {cpabeEncryptSlopeCI:,.0f} µs",
    )
    report = report.replace(
        "{{CpabeCiphertextSlope}}",
        f"+{cpabeCiphertextSlopeBytes:.0f} ± {cpabeCiphertextSlopeCI:.0f} B",
    )
    report = report.replace(
        "{{CpabeStoredKeySlope}}",
        f"+{cpabeStoredKeySlopeBytes:.0f} ± {cpabeStoredKeySlopeCI:.0f} B",
    )
    report = report.replace("{{CpabeEncryptRSquared}}", f"{cpabeEncryptRSquared:.6f}")
    report = report.replace(
        "{{CpabeCiphertextRSquared}}", f"{cpabeCiphertextRSquared:.6f}"
    )
    report = report.replace(
        "{{CpabeStoredKeyRSquared}}", f"{cpabeStoredKeyRSquared:.6f}"
    )
    report = report.replace(
        "{{RsaSubscriberEncryptSlope}}",
        f"+{rsaEncryptSlopeMicros:,.2f} ± {rsaEncryptSlopeCI:,.2f} µs",
    )
    report = report.replace(
        "{{RsaSubscriberTotalCiphertextSlope}}",
        f"+{rsaTotalCiphertextSlopeBytes:.0f} B",
    )
    report = report.replace(
        "{{RsaSubscriberEncryptRSquared}}", f"{rsaEncryptRSquared:.6f}"
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

    # Low/High mirror Min/Max because CP-ABE ciphertext grows with attribute count,
    # and ATTRIBUTE_COUNTS is read as ascending everywhere else in this script.
    report = report.replace(
        "{{BytesCrossoverLow}}", f"{crossoverSummary.BytesCrossoverMin:,.1f}"
    )
    report = report.replace(
        "{{BytesCrossoverHigh}}", f"{crossoverSummary.BytesCrossoverMax:,.1f}"
    )
    report = report.replace(
        "{{BytesCrossoverMin}}", f"{crossoverSummary.BytesCrossoverMin:,.1f}"
    )
    report = report.replace(
        "{{BytesCrossoverMax}}", f"{crossoverSummary.BytesCrossoverMax:,.1f}"
    )
    report = report.replace(
        "{{BytesRsaThroughMin}}",
        f"{int(crossoverSummary.BytesCrossoverMin):,}",
    )
    report = report.replace(
        "{{BytesRsaThroughMax}}",
        f"{int(crossoverSummary.BytesCrossoverMax):,}",
    )
    report = report.replace(
        "{{CpabeDecryptSlope}}",
        f"+{cpabeDecryptSlopeMicros:,.0f} ± {cpabeDecryptSlopeCI:,.0f} µs",
    )
    report = report.replace("{{CpabeDecryptRSquared}}", f"{cpabeDecryptRSquared:.6f}")

    # Time metrics are reported as power-law exponents; size metrics stay linear.
    report = report.replace(
        "{{RsaKeyBitsEncryptExponent}}",
        f"n^{rsaKeyBitsEncryptExponent:.2f} ± {rsaKeyBitsEncryptExponentCI:.2f}",
    )
    report = report.replace(
        "{{RsaKeyBitsDecryptExponent}}",
        f"n^{rsaKeyBitsDecryptExponent:.2f} ± {rsaKeyBitsDecryptExponentCI:.2f}",
    )
    report = report.replace(
        "{{RsaKeyBitsKeygenExponent}}",
        f"n^{rsaKeyBitsKeygenExponent:.2f} ± {rsaKeyBitsKeygenExponentCI:.2f}",
    )
    report = report.replace(
        "{{RsaKeyBitsEncryptRSquared}}", f"{rsaKeyBitsEncryptRSquared:.6f}"
    )
    report = report.replace(
        "{{RsaKeyBitsDecryptRSquared}}", f"{rsaKeyBitsDecryptRSquared:.6f}"
    )
    report = report.replace(
        "{{RsaKeyBitsKeygenRSquared}}", f"{rsaKeyBitsKeygenRSquared:.6f}"
    )

    # Scaled to 1024 bits, because a per-bit byte slope is unreadable. The CI scales identically.
    report = report.replace(
        "{{RsaKeyBitsCiphertextSlope}}",
        f"+{rsaKeyBitsCiphertextSlopeBytes * 1024.0:,.0f} "
        f"± {rsaKeyBitsCiphertextSlopeCI * 1024.0:,.0f} B / 1024 bits",
    )
    report = report.replace(
        "{{RsaKeyBitsStoredKeySlope}}",
        f"+{rsaKeyBitsStoredKeySlopeBytes * 1024.0:,.0f} "
        f"± {rsaKeyBitsStoredKeySlopeCI * 1024.0:,.0f} B / 1024 bits",
    )
    report = report.replace(
        "{{RsaKeyBitsCiphertextRSquared}}", f"{rsaKeyBitsCiphertextRSquared:.6f}"
    )
    report = report.replace(
        "{{RsaKeyBitsStoredKeyRSquared}}", f"{rsaKeyBitsStoredKeyRSquared:.6f}"
    )

    report = report.replace(
        "{{EncryptCpuCrossoverLow}}",
        f"{cpuCrossoverSummary.EncryptCrossoverMin:,.0f}",
    )
    report = report.replace(
        "{{EncryptCpuCrossoverHigh}}",
        f"{cpuCrossoverSummary.EncryptCrossoverMax:,.0f}",
    )
    report = report.replace(
        "{{CpuRsaThroughMin}}",
        f"{int(cpuCrossoverSummary.EncryptCrossoverMin):,}",
    )
    report = report.replace(
        "{{CpuRsaThroughMax}}",
        f"{int(cpuCrossoverSummary.EncryptCrossoverMax):,}",
    )
    report = report.replace("{{BandwidthToCpuGapMin}}", f"{cpuGapMin:,.0f}")
    report = report.replace("{{BandwidthToCpuGapMax}}", f"{cpuGapMax:,.0f}")

    report = report.replace(
        "{{DecryptPenaltyMin}}", f"{cpuCrossoverSummary.DecryptPenaltyMin:,.1f}"
    )
    report = report.replace(
        "{{DecryptPenaltyMax}}", f"{cpuCrossoverSummary.DecryptPenaltyMax:,.1f}"
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
        [],
        "Policy Attributes",
        "CP-ABE Scaling with Policy Attribute Count",
        CPABE_PNG_FILE,
    )

    # Decrypt is swept alongside encrypt so audience-independence is observed, not asserted.
    # Keygen is absent because the key size is fixed across this sweep.
    PlotSweep(
        results,
        "RSASubscribers",
        SUBSCRIBER_COUNTS,
        ["encrypt", "decrypt"],
        [],
        "Subscribers",
        f"RSA Scaling with Subscriber Count (Fixed Key: {FIXED_RSA_KEY_BITS} bits)",
        RSA_SUBSCRIBERS_PNG_FILE,
        fixedDecryptCaseId=(f"decrypt/RSASubscriberFixedKey/{FIXED_RSA_KEY_BITS}"),
    )

    PlotSweep(
        results,
        "RSAKeyBits",
        RSA_KEY_BITS_LIST,
        OPERATIONS,
        [],
        "RSA Key Bits",
        "RSA Scaling with Key Size (1 Subscriber)",
        RSA_KEY_BITS_PNG_FILE,
    )

    # Compute the measured bandwidth crossover used by the plot and explanation.
    crossoverSummary: CrossoverSummary = ComputeCrossoverSummary(results)

    # The publisher- and subscriber-side CPU pictures, alongside the bandwidth one.
    cpuCrossoverSummary: CpuCrossoverSummary = ComputeCpuCrossoverSummary(results)

    PlotCrossover(crossoverSummary)
    PlotEncryptCpuCrossover(cpuCrossoverSummary)
    PlotDecryptCpuCrossover(results)
    PlotEncryptDecryptAsymmetry(results)

    WriteHtmlReport(results, crossoverSummary, cpuCrossoverSummary)


if __name__ == "__main__":
    Main()
