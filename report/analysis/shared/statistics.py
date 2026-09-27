from statistics import fmean

from scipy import stats

from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import EnergyCase
from report.model.macro.macro_aggregation import MacroAggregation
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.memory.memory_case import MemoryCase
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import NS_PER_OP

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
    baseline_cases: list[EnergyCase],
    timing_aggregations: list[TimingAggregation],
) -> tuple[list[float], list[float]]:

    means = []
    confidence_intervals = []
    idle_power_w = fmean(
        fmean(sample.power_w for sample in case.samples) for case in baseline_cases
    )

    for aggregation in aggregations:

        timing_aggregation = next(
            timing
            for timing in timing_aggregations
            if timing.algorithm == aggregation.algorithm
            and timing.operation == aggregation.operation
            and timing.parameter == aggregation.parameter
            and timing.parameter_value == aggregation.parameter_value
        )
        mean_latency_s = (
            fmean(case.measurements[NS_PER_OP] for case in timing_aggregation.cases)
            / NS_PER_SECOND
        )

        # Timing and energy runs are independent. Hold the timing mean fixed;
        # the confidence interval reflects variation across energy repetitions.
        values = _joules_per_operation(aggregation, idle_power_w, mean_latency_s)

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

        value_mean, confidence_interval = memory_case_statistics(
            aggregation.cases,
            measurement,
        )

        means.append(value_mean)
        confidence_intervals.append(confidence_interval)

    return means, confidence_intervals


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


# Calculate energy per operation using the matching case's mean timing latency
def _joules_per_operation(
    aggregation: EnergyAggregation,
    idle_power_w: float,
    mean_latency_s: float,
) -> list[float]:

    values = []

    for case in aggregation.cases:

        # CSV samples already contain only the UM24C measurement window.
        load_power_w = fmean(sample.power_w for sample in case.samples)
        energy_per_operation_joules = (load_power_w - idle_power_w) * mean_latency_s

        values.append(energy_per_operation_joules)

    return values


# Treat repetitions, rather than messages within a repetition, as the samples
def macro_latency_statistics(
    aggregations: list[MacroAggregation],
) -> tuple[list[float], list[float]]:

    means = []
    confidence_intervals = []

    for aggregation in aggregations:

        values = [
            fmean(
                case.subscriber_timestamps[message_id] - started
                for message_id, started in case.publisher_timestamps.items()
            )
            for case in aggregation.cases
        ]
        value_mean, confidence_interval = _mean_and_confidence_interval(values)
        means.append(value_mean)
        confidence_intervals.append(confidence_interval)

    return means, confidence_intervals


# CPU cycles are one total per endpoint per repetition of the fixed workload
def macro_cycle_statistics(
    aggregations: list[MacroAggregation],
) -> dict[str, tuple[list[float], list[float]]]:

    publisher_means = []
    publisher_cis = []
    subscriber_means = []
    subscriber_cis = []

    for aggregation in aggregations:

        publisher_mean, publisher_ci = _mean_and_confidence_interval(
            [case.publisher_cycles for case in aggregation.cases]
        )
        subscriber_mean, subscriber_ci = _mean_and_confidence_interval(
            [case.subscriber_cycles for case in aggregation.cases]
        )
        publisher_means.append(publisher_mean)
        publisher_cis.append(publisher_ci)
        subscriber_means.append(subscriber_mean)
        subscriber_cis.append(subscriber_ci)

    return {
        "publisher": (publisher_means, publisher_cis),
        "subscriber": (subscriber_means, subscriber_cis),
    }
