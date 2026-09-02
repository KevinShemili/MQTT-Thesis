from statistics import fmean

import numpy as np
from scipy import stats

from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import NS_PER_OP, EnergySample
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import MemoryCase
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
    baseline_samples: list[EnergySample],
) -> tuple[list[float], list[float]]:

    means = []
    confidence_intervals = []
    idle_power_w = fmean(sample.power_w for sample in baseline_samples)

    for aggregation in aggregations:

        values = _joules_per_operation(aggregation, idle_power_w)

        value_mean, confidence_interval = _mean_and_confidence_interval(values)

        means.append(value_mean)
        confidence_intervals.append(confidence_interval)

    return means, confidence_intervals


# Calculate mean and confidence interval for independent memory cases
def memory_case_statistics(
    cases: list[MemoryCase],
    measurement: str,
) -> tuple[float, float]:

    values = [case.measurements[measurement] for case in cases]

    return _mean_and_confidence_interval(values)


# Calculate means and confidence intervals for a memory measurement
def memory_statistics(
    aggregations: list[MemoryAggregation],
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


# Calculate distribution statistics for a timing measurement
def timing_distribution_statistics(
    aggregations: list[TimingAggregation],
    measurement: str,
) -> tuple[
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
]:

    medians = []
    minimums = []
    maximums = []
    first_quartiles = []
    third_quartiles = []
    interquartile_ranges = []

    for aggregation in aggregations:

        values = [case.measurements[measurement] for case in aggregation.cases]
        first_quartile, median, third_quartile = np.quantile(
            values,
            [0.25, 0.5, 0.75],
            method="linear",
        )

        medians.append(float(median))
        minimums.append(min(values))
        maximums.append(max(values))
        first_quartiles.append(float(first_quartile))
        third_quartiles.append(float(third_quartile))
        interquartile_ranges.append(float(third_quartile - first_quartile))

    return (
        medians,
        minimums,
        maximums,
        first_quartiles,
        third_quartiles,
        interquartile_ranges,
    )


# Calculate a linear regression and the slope's 95% confidence interval
def linear_regression_statistics(
    x_values: list[float] | list[int],
    y_values: list[float],
) -> tuple[float, float, float, float]:

    regression = stats.linregress(x_values, y_values)
    slope_confidence_interval = float(
        stats.t.ppf(0.975, len(x_values) - 2) * regression.stderr
    )

    return (
        float(regression.slope),
        float(regression.intercept),
        float(regression.rvalue**2),
        slope_confidence_interval,
    )


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
    idle_power_w: float,
) -> list[float]:

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
