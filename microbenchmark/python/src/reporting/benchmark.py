from __future__ import annotations
from collections import defaultdict
from .statistics import (
    get_student_t_critical_95,
    mean_and_confidence_interval,
    median,
    percentile,
)

# Features we have collected across all benchmarks are listed here as constants,
# so that they can be referenced in a single place
NS_PER_OP = "ns/op"
MB_PER_SECOND = "MB/s"
WIRE_OVERHEAD_BYTES = "wire_overhead_bytes/op"
ENVELOPE_BYTES = "envelope_bytes/op"
RAW_BYTES = "raw_bytes/op"
CIPHERTEXT_BYTES = "ciphertext_bytes"
TOTAL_CIPHERTEXT_BYTES = "total_ciphertext_bytes"
STORED_KEY_BYTES = "stored_key_bytes"
THROTTLED = "throttled"

# The following constants are used to convert ns to µs and to ms
NS_PER_MICROSECOND = 1000.0
NS_PER_MILLISECOND = 1000000.0


# Everything that can be said about the repeated samples of one feature of one case.
# A caller reads whichever statistics it needs: a latency table reads mean and ci, a
# key generation table reads median, minimum, maximum and iqr, a plot reads either.
#
# Mean and CI describe a symmetric measurement, whereas median, quartiles and the
# extremes also describe a skewed one, ex. RSA key generation, whose cost is a
# probabilistic prime search with a long right tail that a mean alone would hide
class Measurement:
    def __init__(self, values: list[float]) -> None:

        self.values = values
        self.count = len(values)

        self.mean, self.ci = mean_and_confidence_interval(
            values,
            # Each measurement carries its own sample count, so it also decides
            # its own t. Cases collected over a different number of runs than the
            # rest of the benchmark are therefore still given the correct multiplier
            get_student_t_critical_95(self.count - 1),
        )

        self.median = median(values)
        self.minimum = min(values)
        self.maximum = max(values)

        self.first_quartile = percentile(values, 0.25)
        self.third_quartile = percentile(values, 0.75)

        # Width of the middle half of the samples, the spread that ignores the tails
        self.iqr = self.third_quartile - self.first_quartile

    # Same measurement expressed in another unit, ex. ns -> µs. Every statistic held
    # here is linear in the samples, so scaling the samples and reducing them again
    # gives exactly the scaled statistics
    def scale_unit(self, divisor: float) -> Measurement:
        return Measurement([value / divisor for value in self.values])


# Collects the measurements of one feature across a sweep, ex. the encrypt latency
# at every subscriber count. Holds the measurements themselves rather than a single
# extracted statistic, so the same sweep can be drawn as mean ± CI or as a distribution
class FeatureSweep:
    def __init__(self) -> None:
        self.sweep_values: list[float] = []
        self.measurements: list[Measurement] = []

    def add(self, sweep_value: float, measurement: Measurement) -> None:
        self.sweep_values.append(sweep_value)
        self.measurements.append(measurement)

    @property
    def means(self) -> list[float]:
        return [measurement.mean for measurement in self.measurements]

    @property
    def ci(self) -> list[float]:
        return [measurement.ci for measurement in self.measurements]

    @property
    def medians(self) -> list[float]:
        return [measurement.median for measurement in self.measurements]

    @property
    def minimums(self) -> list[float]:
        return [measurement.minimum for measurement in self.measurements]

    @property
    def maximums(self) -> list[float]:
        return [measurement.maximum for measurement in self.measurements]

    @property
    def first_quartiles(self) -> list[float]:
        return [measurement.first_quartile for measurement in self.measurements]

    @property
    def third_quartiles(self) -> list[float]:
        return [measurement.third_quartile for measurement in self.measurements]


# One benchmark case, ex. "encrypt/PSK/16". Collects the repeated runs of that case as
# they are read from the file, then reduces each feature's samples to a Measurement
class CaseSummary:
    def __init__(self) -> None:
        self.iterations = 0  # total iterations across the repeated runs
        self.samples: dict[str, list[float]] = defaultdict(list)
        self.features: dict[str, Measurement] = {}

    def add_run(self, iterations: int, feature_values: dict[str, float]) -> None:

        self.iterations += iterations

        for feature_name, value in feature_values.items():
            self.samples[feature_name].append(value)

    def summarize(self) -> None:
        self.features = {
            feature_name: Measurement(values)
            for feature_name, values in self.samples.items()
        }

    def get_feature(self, feature_name: str) -> Measurement:
        return self.features[feature_name]

    # Whether any repetition of this case ran while the Raspberry Pi firmware was
    # throttling the clock. One throttled repetition is enough, the case then carries
    # a pessimistic bound and is reported as such
    @property
    def throttled(self) -> bool:
        return THROTTLED in self.features and self.features[THROTTLED].maximum > 0

    # Case latency, by default in µs. Slower operations ex. key generation pass
    # NS_PER_MILLISECOND instead
    def latency(self, divisor: float = NS_PER_MICROSECOND) -> Measurement:
        return self.features[NS_PER_OP].scale_unit(divisor)


# Full statistical summary of the benchmark including all of the inner cases
class BenchmarkSummary:
    def __init__(self, cases: dict[str, CaseSummary]) -> None:
        self.cases = cases

    # Based on operation (ex. encrypt) & group (ex. PSK) & sweep_value (ex. 16), return the corresponding case summary
    def get_case_summary(
        self, operation: str, group: str, sweep_value: int
    ) -> CaseSummary:
        return self.cases[_generate_case_id(operation, group, sweep_value)]

    # Collects all data of a sweep of just one feature
    def sweep_features(
        self,
        operation: str,
        group: str,
        sweep_values: list[int],
        feature_name: str,
        divisor: float = 1.0,  # to convert to another measurement unit if desired
    ) -> FeatureSweep:

        series = FeatureSweep()

        for sweep_value in sweep_values:

            measurement = (
                self.get_case_summary(operation, group, sweep_value)
                .get_feature(feature_name)
                .scale_unit(divisor)
            )

            series.add(sweep_value, measurement)

        return series

    # Total iterations of all cases across all runs
    @property
    def total_iterations(self) -> int:
        return sum(case.iterations for case in self.cases.values())


# 1. Reads benchmark's output file through _read_rows() -> Groups repeated runs of each case together
# 2. After grouping reduces every feature of every case to a Measurement
# 3. Returns a BenchmarkSummary containing all cases with their statistics
def load_results(
    filepath: str,
    prefix: str,
    value_suffix: str = "",
) -> BenchmarkSummary:

    # In cases now we have all the repeated runs of each case grouped together, ex. for "encrypt/PSK/16" we have 3 runs with their feature values
    cases = _read_rows(
        filepath,
        prefix,
        value_suffix,
    )

    for case in cases.values():
        case.summarize()

    return BenchmarkSummary(cases=cases)


# Throttle flag of each given case, in the order the rows of a table are built. Returns
# None where the benchmark carries no throttle readings at all, ex. output produced on a
# machine without vcgencmd, so that a report claims measurements were thermally clean
# only where it actually knows that they were
def throttle_flags(cases: list[CaseSummary]) -> list[bool] | None:

    if not any(THROTTLED in case.features for case in cases):
        return None

    return [case.throttled for case in cases]


# Builds a sort of ID for identifying one benchmark case,
# for example if operation="encrypt" & group="PSK" & sweep_value=16 then -> "encrypt/PSK/16".
def _generate_case_id(operation: str, group: str, sweep_value: int) -> str:
    return f"{operation}/{group}/{sweep_value}"


# Reads benchmark's output file & groups its rows by the case ID they belong to
def _read_rows(
    filepath: str,
    prefix: str,  # something like "BenchmarkPayloadScaling"
    value_suffix: str,  # something like "B" for bytes, which comes after the sweep value in the benchmark's output
) -> dict[str, CaseSummary]:

    rows: dict[str, CaseSummary] = {}

    with open(filepath, "r", encoding="utf-8") as file:

        for line in file:
            fields = line.split()

            # Skip the goos/goarch/cpu
            if len(fields) == 0 or not fields[0].startswith(prefix):
                continue

            # After skip we encounter rows that start like "BenchmarkPayloadScalingEncrypt/PSK/16B-4",
            # which we split into operation="Encrypt", group="PSK", sweep value=16B-4
            operation, group, sweep_text = fields[0][len(prefix) :].split("/")[:3]

            # Remove suffix from 16B-4 to get the sweep value as an integer, ex. 16
            sweep_value = int(sweep_text.split("-")[0].removesuffix(value_suffix))

            # Check if data already exists for this case,
            # otherwise create a fresh CaseSummary object
            case = rows.setdefault(
                _generate_case_id(operation.lower(), group, sweep_value),
                CaseSummary(),
            )

            # Each feature of each row follows a "<feature value> <feature unit>" pattern, for example "123456 ns/op" or "123.45 MB/s",
            # so we iterate over the fields in pairs, starting from index 2, collecting one sample per feature
            case.add_run(
                int(fields[1]),
                {
                    fields[index + 1]: float(fields[index])
                    for index in range(2, len(fields) - 1, 2)
                },
            )

    return rows
