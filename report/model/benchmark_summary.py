from .energy.energy_aggregation import EnergyAggregation
from .energy.energy_case import EnergySample
from .memory.memory_aggregation import MemoryAggregation
from .memory.memory_case import MemoryCase
from .timing.timing_aggregation import TimingAggregation


# Groups together all aggregations for a given benchmark scenario
class BenchmarkSummary:

    def __init__(self):
        self.timing_aggregations: list[TimingAggregation] = []

        self.memory_baseline_cases: list[MemoryCase] = []
        self.memory_aggregations: list[MemoryAggregation] = []

        self.energy_baseline_samples: list[EnergySample] = []
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

    # Find a specific memory aggregation
    def find_memory_aggregation(
        self,
        algorithm: str,
        operation: str,
        parameter: str,
        parameter_value: int,
    ) -> MemoryAggregation | None:

        for aggregation in self.memory_aggregations:

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
