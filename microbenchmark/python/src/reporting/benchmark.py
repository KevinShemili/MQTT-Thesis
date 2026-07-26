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


@dataclass
class BenchmarkMetrics:
    iterations: list[int] = field(default_factory=list)
    samples_by_unit: dict[str, list[float]] = field(default_factory=dict)

    @property
    def ns_per_op(self) -> list[float]:
        return self.samples_by_unit[NS_PER_OP]

    def samples(self, unit: str) -> list[float]:
        return self.samples_by_unit.get(unit, [])

    def add(self, unit: str, value: float) -> None:
        self.samples_by_unit.setdefault(unit, []).append(value)


@dataclass(frozen=True)
class BenchmarkSpec:
    prefix: str
    value_suffix: str = ""
    required_units: tuple[str, ...] = (NS_PER_OP,)
    optional_units: tuple[str, ...] = ()


@dataclass
class Series:
    x: list[float] = field(default_factory=list)
    means: list[float] = field(default_factory=list)
    ci_halfs: list[float] = field(default_factory=list)


def case_id(operation: str, group: str, sweep_value: int | str) -> str:
    return f"{operation}/{group}/{sweep_value}"


def parse_benchmark_file(
    filepath: str,
    spec: BenchmarkSpec,
) -> dict[str, BenchmarkMetrics]:

    results: dict[str, BenchmarkMetrics] = {}

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields = line.split()

            # Skip the goos/goarch/cpu
            if len(fields) == 0 or not fields[0].startswith(spec.prefix):
                continue

            # "Encrypt/PSK/16B-4" -> operation, compared group, sweep value text.
            operation, group, sweep_text = fields[0][len(spec.prefix) :].split("/")[:3]

            # Strip the -4 suffix
            sweep_value = int(sweep_text.split("-")[0].removesuffix(spec.value_suffix))

            metrics = results.setdefault(
                case_id(operation.lower(), group, sweep_value),
                BenchmarkMetrics(),
            )
            metrics.iterations.append(int(fields[1]))

            # Read each trailing <value> <unit> pair
            line_samples = {
                fields[index + 1]: float(fields[index])
                for index in range(2, len(fields) - 1, 2)
            }

            for unit in spec.required_units:
                metrics.add(unit, line_samples[unit])

            for unit in spec.optional_units:
                if unit in line_samples:
                    metrics.add(unit, line_samples[unit])

    return results


def load_results(filepath: str, spec: BenchmarkSpec) -> dict[str, BenchmarkMetrics]:
    try:
        return parse_benchmark_file(filepath, spec)
    except FileNotFoundError:
        sys.exit(f"[error] {filepath} not found — run the benchmark first")


def sum_iterations(metrics: BenchmarkMetrics) -> int:
    return sum(metrics.iterations)


def total_iterations(results: dict[str, BenchmarkMetrics]) -> int:
    return sum(sum_iterations(metrics) for metrics in results.values())


def require_mean(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
    unit: str,
    bench_file: str,
    missing_label: str = "benchmark case",
) -> float:

    metrics = results.get(benchmark_case_id)

    if metrics is None or len(metrics.samples(unit)) == 0:
        sys.exit(
            f"[error] missing {missing_label} '{benchmark_case_id}' in {bench_file}"
        )

    return mean(metrics.samples(unit))


def require_mean_micros(
    results: dict[str, BenchmarkMetrics],
    benchmark_case_id: str,
    bench_file: str,
) -> float:
    return require_mean(results, benchmark_case_id, NS_PER_OP, bench_file) / (
        NS_PER_MICROSECOND
    )


def collect_series(
    results: dict[str, BenchmarkMetrics],
    cases: list[tuple[int, str]],
    unit: str,
    t_critical: float,
    divisor: float = 1.0,
) -> Series:

    series = Series()

    for sweep_value, benchmark_case_id in cases:

        metrics = results.get(benchmark_case_id)
        if metrics is None:
            continue

        mean_value, ci_half = mean_and_confidence_interval(
            metrics.samples_by_unit[unit], t_critical
        )

        series.x.append(sweep_value)
        series.means.append(mean_value / divisor)
        series.ci_halfs.append(ci_half / divisor)

    return series


def collect_means(
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
