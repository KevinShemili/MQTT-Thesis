import sys
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
# 3. ci_halfs are the confidence-interval half-widths for each sweep value
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

    def samples(self, unit: str) -> list[float]:

        values: list[float] = []

        for run in self.runs:
            if unit in run.measurements_by_unit:
                values.append(run.measurements_by_unit[unit])

        return values


# How each row of benchmark's output is interpreted:
# 1. Prefix identifies relevant benchmark lines
# 2. Value suffix is stripped from the sweep value ex. "B" from "16B"
# 3. Required units must be present in the benchmark output
# 4. Optional units may be present in the benchmark output
@dataclass(frozen=True)
class BenchmarkParserConfig:
    prefix: str
    value_suffix: str = ""
    required_units: tuple[str, ...] = (NS_PER_OP,)
    optional_units: tuple[str, ...] = ()


# Builds ID for identifying one benchmark case
# Example: operation="encrypt", group="PSK", sweep_value=16 -> "encrypt/PSK/16".
def generate_case_id(operation: str, group: str, sweep_value: int | str) -> str:
    return f"{operation}/{group}/{sweep_value}"


# Reads benchmark's output file & converts its rows into structured BenchmarkMetrics objects, grouped by benchmark case IDs, so (case_id | BenchmarkMetrics).
# A dictionary groups repeated benchmark runs by identifiers such as
# "encrypt/PSK/16", with each entry containing iterations & measured values among repeated runs
def parse_benchmark_file(
    filepath: str,
    spec: BenchmarkParserConfig,
) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields = line.split()

            # Skip the goos/goarch/cpu
            if len(fields) == 0 or not fields[0].startswith(spec.prefix):
                continue

            # "BenchmarkPayloadScalingEncrypt/PSK/16B-4"
            # becomes operation="Encrypt", group="PSK", sweep_text="16B-4".
            operation, group, sweep_text = fields[0][len(spec.prefix) :].split("/")[:3]

            # Remove the Go CPU suffix such as "-4"
            sweep_value = int(sweep_text.split("-")[0].removesuffix(spec.value_suffix))

            # Find the stored metrics for this benchmark case.
            # If this is its first occurrence, create an empty BenchmarkMetrics object.
            metrics = results.setdefault(
                generate_case_id(operation.lower(), group, sweep_value),
                BenchmarkMetrics(),
            )

            # Convert the benchmark row's "<value> <unit>" pairs into measurements by unit.
            line_samples: dict[str, float] = {}

            for index in range(2, len(fields) - 1, 2):
                unit: str = fields[index + 1]
                line_samples[unit] = float(fields[index])

            # Keep only measurements configured for this benchmark scenario.
            run_measurements: dict[str, float] = {}

            for unit in spec.required_units:
                run_measurements[unit] = line_samples[unit]

            for unit in spec.optional_units:
                if unit in line_samples:
                    run_measurements[unit] = line_samples[unit]

            # Store this benchmark output row as one complete repeated run.
            metrics.runs.append(
                BenchmarkMetrics.SingleRun(
                    iteration_count=int(fields[1]),
                    measurements_by_unit=run_measurements,
                )
            )

    return results


# Total iterations considering also total number of runs
def calculate_iterations(metrics: BenchmarkMetrics) -> int:
    iteration_total: int = 0

    for run in metrics.runs:
        iteration_total += run.iteration_count

    return iteration_total


# Total iterations across all runs, across all benchmark cases
def calculate_total_iterations(results: dict[str, BenchmarkMetrics]) -> int:
    return sum(calculate_iterations(metrics) for metrics in results.values())


# Take mean of measurements resulting from repeated runs of a benchmark case
def calculate_mean(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
    unit: str,
) -> float:

    metrics = results.get(benchmark_case_id)

    if metrics is None or len(metrics.samples(unit)) == 0:
        sys.exit()

    return mean(metrics.samples(unit))


# Same but returns µs/op instead of ns/op
def calculate_mean_micros(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
) -> float:
    return calculate_mean(
        results,
        benchmark_case_id,
        NS_PER_OP,
    ) / (NS_PER_MICROSECOND)


# Collect multiple BenchmarkMetrics into a single final summary, indicating mean and confidence interval
def produce_summary(
    results: dict[str, BenchmarkMetrics],
    cases: list[tuple[int, str]],
    unit: str,
    t_critical: float,
    divisor: float = 1.0,
) -> BenchmarkSummaryData:

    summary = BenchmarkSummaryData()

    for sweep_value, benchmark_case_id in cases:

        metrics = results.get(benchmark_case_id)
        if metrics is None:
            continue

        samples: list[float] = metrics.samples(unit)
        mean_value, ci_half = mean_and_confidence_interval(samples, t_critical)

        summary.sweep_values.append(sweep_value)
        summary.means.append(mean_value / divisor)
        summary.ci_halfs.append(ci_half / divisor)

    return summary


# Like produce_summary() but returns just means without CIs
def produce_summary_no_ci(
    results: dict[str, BenchmarkMetrics],
    cases: list[tuple[int, str]],
    unit: str,
    divisor: float = 1.0,
) -> tuple[list[float], list[float]]:

    x_values: list[float] = []
    mean_values: list[float] = []

    for sweep_value, benchmark_case_id in cases:

        metrics = results.get(benchmark_case_id)
        if metrics is None or len(metrics.samples(unit)) == 0:
            continue

        x_values.append(sweep_value)
        mean_values.append(mean(metrics.samples(unit)) / divisor)

    return x_values, mean_values
