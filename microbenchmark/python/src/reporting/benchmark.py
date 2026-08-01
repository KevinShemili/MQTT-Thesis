from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass, field
from .statistics import mean_and_confidence_interval

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

# The following constant is used to convert ns to µs
NS_PER_MICROSECOND = 1000.0


# Mean & CI of one feature across all runs of one case
@dataclass(frozen=True)
class FeatureMeasurement:
    mean: float
    ci: float

    # Same measurement expressed in another unit, ex. ns -> µs
    def scale_unit(self, divisor: float) -> FeatureMeasurement:
        return FeatureMeasurement(self.mean / divisor, self.ci / divisor)

    # Create instance of FeatureMeasurement from a list of values
    @staticmethod
    def create(values: list[float], t_critical: float) -> FeatureMeasurement:
        mean, ci = mean_and_confidence_interval(values, t_critical)
        return FeatureMeasurement(mean, ci)


# Collects all the data of a sweep of just one feature, ready for plotting
@dataclass
class FeatureSweep:
    sweep_values: list[float] = field(default_factory=list)
    means: list[float] = field(default_factory=list)
    ci: list[float] = field(default_factory=list)


# One benchmark case with iterations & feature summary
@dataclass(frozen=True)
class CaseSummary:
    iterations: int
    features: dict[str, FeatureMeasurement]

    def get_feature(self, feature_name: str) -> FeatureMeasurement:
        return self.features[feature_name]

    @property
    def get_latency_in_micros(self) -> FeatureMeasurement:
        return self.features[NS_PER_OP].scale_unit(NS_PER_MICROSECOND)


# Full statistical summary of the benchmark including all of the inner cases
@dataclass(frozen=True)
class BenchmarkSummary:
    cases: dict[str, CaseSummary]

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
        with_ci: bool = False,
    ) -> FeatureSweep:

        series = FeatureSweep()

        for sweep_value in sweep_values:

            measurement = (
                self.get_case_summary(operation, group, sweep_value)
                .get_feature(feature_name)
                .scale_unit(divisor)
            )

            series.sweep_values.append(sweep_value)
            series.means.append(measurement.mean)

            if with_ci:
                series.ci.append(measurement.ci)

        return series

    # Total iterations of all cases across all runs
    @property
    def get_total_iterations(self) -> int:
        return sum(case.iterations for case in self.cases.values())


# 1. Reads benchmark's output file through _read_rows() -> Groups repeated runs of each case together -> Stores them in _CaseRuns
# 2. After grouping calculate mean & CI of each feature of each case -> Stores them in CaseSummary
# 3. Returns a BenchmarkSummary containing all cases with their statistics
def load_results(
    filepath: str,
    prefix: str,
    t_critical: float,
    value_suffix: str = "",
) -> BenchmarkSummary:

    # In case_runs now we have all the repeated runs of each case grouped together, ex. for "encrypt/PSK/16" we have 3 runs with their feature values
    case_runs = _read_rows(
        filepath,
        prefix,
        value_suffix,
    )

    summarized_cases: dict[str, CaseSummary] = {}

    for case_id, runs in case_runs.items():

        summarized_features: dict[str, FeatureMeasurement] = {}

        for feature_name, values in runs.feature_values.items():

            # Reduce all repeated values of one feature to mean and CI.
            measurement = FeatureMeasurement.create(
                values,
                t_critical,
            )

            summarized_features[feature_name] = measurement

        summarized_cases[case_id] = CaseSummary(
            iterations=runs.iterations,
            features=summarized_features,
        )

    return BenchmarkSummary(cases=summarized_cases)


# Builds a sort of ID for identifying one benchmark case,
# for example if operation="encrypt" & group="PSK" & sweep_value=16 then -> "encrypt/PSK/16".
def _generate_case_id(operation: str, group: str, sweep_value: int) -> str:
    return f"{operation}/{group}/{sweep_value}"


# The repeated runs of one case, as they are read from the file,
# before they are reduced to statistics
@dataclass
class _CaseRuns:
    iterations: int = 0  # total iterations across the repeated runs
    feature_values: dict[str, list[float]] = field(
        default_factory=lambda: defaultdict(list)
    )


# Reads benchmark's output file & groups its rows by the case ID they belong to
def _read_rows(
    filepath: str,
    prefix: str,  # something like "BenchmarkPayloadScaling"
    value_suffix: str,  # something like "B" for bytes, which comes after the sweep value in the benchmark's output
) -> dict[str, _CaseRuns]:

    rows: dict[str, _CaseRuns] = {}

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
            # otherwise create a fresh _CaseRuns object
            runs = rows.setdefault(
                _generate_case_id(operation.lower(), group, sweep_value),
                _CaseRuns(),
            )

            runs.iterations += int(fields[1])

            # Each feature of each row follows a "<feature value> <feature unit>" pattern, for example "123456 ns/op" or "123.45 MB/s",
            # so we iterate over the fields in pairs, starting from index 2, collecting one sample per feature
            for index in range(2, len(fields) - 1, 2):
                runs.feature_values[fields[index + 1]].append(float(fields[index]))

    return rows
