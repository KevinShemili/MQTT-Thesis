from __future__ import annotations
from .case_aggregation import CaseAggregation
from .measurement import THROTTLED


# Groups together all aggregations for a given benchmark scenario
class BenchmarkSummary:

    def __init__(self, aggregations: list[CaseAggregation] | None = None) -> None:
        self.aggregations = [] if aggregations is None else aggregations

    # Find a specific aggregation based on operation, parameter & parameter value
    def find_aggregation(
        self,
        operation: str,
        parameter: str,
        parameter_value: int,
    ) -> CaseAggregation | None:
        for aggregation in self.aggregations:
            if (
                aggregation.operation == operation
                and aggregation.parameter == parameter
                and aggregation.parameter_value == parameter_value
            ):
                return aggregation

        return None

    # Given a list of parameter values, return a list of booleans indicating whether each aggregation experienced throttling
    def get_throttle_flags(
        self,
        operation: str,
        parameter: str,
        parameter_values: list[int],
    ) -> list[bool] | None:

        aggregations = [
            self.find_aggregation(operation, parameter, value)
            for value in parameter_values
        ]

        if not any(
            aggregation is not None
            and not aggregation.out_of_memory
            and aggregation.has_measurement(THROTTLED)
            for aggregation in aggregations
        ):
            return None

        return [
            aggregation is not None
            and not aggregation.out_of_memory
            and aggregation.throttled
            for aggregation in aggregations
        ]
