from statistics import fmean

from scipy import stats

from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import NS_PER_OP
from report.model.timing.timing_aggregation import TimingAggregation

NS_PER_SECOND = 1_000_000_000


# Calculate means and confidence intervals for a timing measurement
def timing_statistics(
    aggregations: list[TimingAggregation],
    measurement: str,
) -> tuple[list[float], list[float]]:

    means = []
    confidence_intervals = []

    for aggregation in aggregations:

        values = [case.measurements[measurement] for case in aggregation.cases]

        value_mean, confidence_interval = _mean_and_confidence_interval(values)

        means.append(value_mean)
        confidence_intervals.append(confidence_interval)

    return means, confidence_intervals


# Calculate energy-per-operation means and confidence intervals
def energy_statistics(
    aggregations: list[EnergyAggregation],
) -> tuple[list[float], list[float]]:

    means = []
    confidence_intervals = []

    for aggregation in aggregations:

        values = _joules_per_operation(aggregation)

        value_mean, confidence_interval = _mean_and_confidence_interval(values)

        means.append(value_mean)
        confidence_intervals.append(confidence_interval)

    return means, confidence_intervals


# Calculate the multiplier used for a 95% confidence interval
def confidence_interval_multiplier(sample_count: int) -> float:
    return float(stats.t.ppf(0.975, sample_count - 1))


# Calculate mean and 95% confidence interval
def _mean_and_confidence_interval(
    values: list[float],
) -> tuple[float, float]:

    value_mean = fmean(values)

    if len(values) == 1:
        return value_mean, 0.0

    confidence_interval = confidence_interval_multiplier(len(values)) * float(
        stats.sem(values)
    )

    return value_mean, confidence_interval


# Calculate energy per operation for every independent energy run
def _joules_per_operation(
    aggregation: EnergyAggregation,
) -> list[float]:

    idle_power_w = fmean(sample.power_w for sample in aggregation.baseline_samples)

    measurement_end = aggregation.warmup_duration + aggregation.measurement_duration

    values = []

    for case in aggregation.cases:

        load_power_w = fmean(
            sample.power_w
            for sample in case.samples
            if aggregation.warmup_duration <= sample.elapsed_s < measurement_end
        )

        operation_time_seconds = case.measurements[NS_PER_OP] / NS_PER_SECOND

        energy_per_operation_joules = (
            load_power_w - idle_power_w
        ) * operation_time_seconds

        values.append(energy_per_operation_joules)

    return values
