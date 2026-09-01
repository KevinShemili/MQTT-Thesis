from .energy.energy_aggregation import EnergyAggregation
from .timing.timing_aggregation import TimingAggregation


# Groups together all aggregations for a given benchmark scenario
class BenchmarkSummary:

    def __init__(self):
        self.timing_aggregations: list[TimingAggregation] = []
        self.energy_aggregations: list[EnergyAggregation] = []

    # Find a specific timing aggregation
    def find_timing_aggregation(
        self,
        algorithm: str,
        operation: str,
        parameter: str,
        parameter_value: int,
    ) -> TimingAggregation | None:

        for aggregation in self.timing_aggregations:

            if (
                aggregation.algorithm == algorithm
                and aggregation.operation == operation
                and aggregation.parameter == parameter
                and aggregation.parameter_value == parameter_value
            ):
                return aggregation

        return None

    # Find a specific energy aggregation
    def find_energy_aggregation(
        self,
        algorithm: str,
        operation: str,
        parameter: str,
        parameter_value: int,
    ) -> EnergyAggregation | None:

        for aggregation in self.energy_aggregations:

            if (
                aggregation.algorithm == algorithm
                and aggregation.operation == operation
                and aggregation.parameter == parameter
                and aggregation.parameter_value == parameter_value
            ):
                return aggregation

        return None
