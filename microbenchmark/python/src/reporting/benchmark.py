from dataclasses import dataclass, field
from .statistics import mean, mean_and_confidence_interval

NS_PER_OP = "ns/op"
MB_PER_SECOND = "MB/s"
WIRE_OVERHEAD_BYTES = "wire_overhead_bytes/op"
ENVELOPE_BYTES = "envelope_bytes/op"
RAW_BYTES = "raw_bytes/op"
CIPHERTEXT_BYTES = "ciphertext_bytes"
TOTAL_CIPHERTEXT_BYTES = "total_ciphertext_bytes"
STORED_KEY_BYTES = "stored_key_bytes"
NS_PER_MICROSECOND = 1000.0


# Represents data ready to be plotted
# 1. sweep_values ex. 16, 32, 64, 128
# 2. means are the mean results for each sweep value
# 3. ci_halfs are the confidence-interval half-widths for each sweep value,
#    left empty when the series is produced without a t multiplier
@dataclass
class BenchmarkSummaryData:
    sweep_values: list[float] = field(default_factory=list)
    means: list[float] = field(default_factory=list)
    ci_halfs: list[float] = field(default_factory=list)


# Store all gathered data from repeated measurements under a single benchmark case ex. "encrypt/PSK/16".
@dataclass
class BenchmarkMetrics:

    @dataclass
    class SingleRun:
        iteration_count: int
        measurements_by_unit: dict[str, float]

    runs: list[SingleRun] = field(default_factory=list)

    @property
    def ns_per_op(self) -> list[float]:
        return self.samples(NS_PER_OP)

    # Measurements of one unit across the repeated runs. Units a benchmark case does not
    # report at all ex. ciphertext size on a decrypt case simply yield no samples
    def samples(self, unit: str) -> list[float]:
        return [
            run.measurements_by_unit[unit]
            for run in self.runs
            if unit in run.measurements_by_unit
        ]


# Builds ID for identifying one benchmark case
# Example: operation="encrypt", group="PSK", sweep_value=16 -> "encrypt/PSK/16".
def generate_case_id(operation: str, group: str, sweep_value: int) -> str:
    return f"{operation}/{group}/{sweep_value}"


# Pairs every sweep value with its benchmark case ID, the form expected by produce_summary()
def build_cases(
    operation: str,
    group: str,
    sweep_values: list[int],
) -> list[tuple[int, str]]:
    return [
        (sweep_value, generate_case_id(operation, group, sweep_value))
        for sweep_value in sweep_values
    ]


# Reads benchmark's output file & converts its rows into structured BenchmarkMetrics objects, grouped by benchmark case IDs, so (case_id | BenchmarkMetrics).
# A dictionary groups repeated benchmark runs by identifiers such as
# "encrypt/PSK/16", with each entry containing iterations & measured values among repeated runs
# 1. prefix identifies the relevant benchmark lines
# 2. value_suffix is stripped from the sweep value ex. "B" from "16B"
def parse_benchmark_file(
    filepath: str,
    prefix: str,
    value_suffix: str = "",
) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields = line.split()

            # Skip the goos/goarch/cpu
            if len(fields) == 0 or not fields[0].startswith(prefix):
                continue

            # "BenchmarkPayloadScalingEncrypt/PSK/16B-4"
            # becomes operation="Encrypt", group="PSK", sweep_text="16B-4".
            operation, group, sweep_text = fields[0][len(prefix) :].split("/")[:3]

            # Remove the Go CPU suffix such as "-4"
            sweep_value = int(sweep_text.split("-")[0].removesuffix(value_suffix))

            # Find the stored metrics for this benchmark case.
            # If this is its first occurrence, create an empty BenchmarkMetrics object.
            metrics = results.setdefault(
                generate_case_id(operation.lower(), group, sweep_value),
                BenchmarkMetrics(),
            )

            # Convert the benchmark row's "<value> <unit>" pairs into measurements by unit.
            measurements_by_unit: dict[str, float] = {}

            for index in range(2, len(fields) - 1, 2):
                measurements_by_unit[fields[index + 1]] = float(fields[index])

            # Store this benchmark output row as one complete repeated run.
            metrics.runs.append(
                BenchmarkMetrics.SingleRun(
                    iteration_count=int(fields[1]),
                    measurements_by_unit=measurements_by_unit,
                )
            )

    return results


# Total iterations considering also total number of runs
def calculate_iterations(metrics: BenchmarkMetrics) -> int:
    return sum(run.iteration_count for run in metrics.runs)


# Total iterations across all runs, across all benchmark cases
def calculate_total_iterations(results: dict[str, BenchmarkMetrics]) -> int:
    return sum(calculate_iterations(metrics) for metrics in results.values())


# Take mean of measurements resulting from repeated runs of a benchmark case
def calculate_mean(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
    unit: str,
) -> float:
    return mean(results[benchmark_case_id].samples(unit))


# Same but returns µs/op instead of ns/op
def calculate_mean_micros(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
) -> float:
    return calculate_mean(results, benchmark_case_id, NS_PER_OP) / NS_PER_MICROSECOND


# Collect multiple BenchmarkMetrics into a single final summary.
# Passing a t multiplier additionally fills in the confidence-interval half-widths
def produce_summary(
    results: dict[str, BenchmarkMetrics],
    cases: list[tuple[int, str]],
    unit: str,
    t_critical: float | None = None,
    divisor: float = 1.0,
) -> BenchmarkSummaryData:

    summary = BenchmarkSummaryData()

    for sweep_value, benchmark_case_id in cases:

        samples = results[benchmark_case_id].samples(unit)

        summary.sweep_values.append(sweep_value)

        if t_critical is None:
            summary.means.append(mean(samples) / divisor)
            continue

        mean_value, ci_half = mean_and_confidence_interval(samples, t_critical)
        summary.means.append(mean_value / divisor)
        summary.ci_halfs.append(ci_half / divisor)

    return summary
