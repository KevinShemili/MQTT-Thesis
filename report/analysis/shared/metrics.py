from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import THROTTLED as ENERGY_THROTTLED
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import THROTTLED as TIMING_THROTTLED

MEGABYTE = 1024 * 1024

NS_PER_MICROSECOND = 1000.0

MICROJOULES_PER_JOULE = 1_000_000


# Check whether each timing aggregation experienced throttling
def collect_timing_throttle_flags(
    aggregations: list[TimingAggregation],
) -> list[bool]:

    return [
        any(case.measurements[TIMING_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Check whether each energy aggregation experienced throttling
def collect_energy_throttle_flags(
    aggregations: list[EnergyAggregation],
) -> list[bool]:

    return [
        any(case.measurements[ENERGY_THROTTLED] > 0 for case in aggregation.cases)
        for aggregation in aggregations
    ]


# Convert nanoseconds to microseconds
def to_microseconds(
    values: list[float],
) -> list[float]:

    return [value / NS_PER_MICROSECOND for value in values]


# Convert joules to microjoules
def to_microjoules(
    values: list[float],
) -> list[float]:

    return [value * MICROJOULES_PER_JOULE for value in values]


# Convert bytes to megabytes
def to_megabytes(
    values: list[float],
) -> list[float]:

    return [value / MEGABYTE for value in values]
