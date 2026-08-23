from __future__ import annotations

import numpy as np
from scipy import stats

from model.case import Case
from model.measurement import THROTTLED


# Aggregates multiple cases across independent runs
class CaseAggregation:

    def __init__(
        self,
        operation: str,  # Encrypt
        parameter: str,  # CPABEAttributes
        parameter_value: int,  # 2
        cases: list[Case] | None = None,  # List of independent cases
        is_out_of_memory: bool = False,  # Possible OOM kill -> no statistics
    ) -> None:
        self.operation = operation
        self.parameter = parameter
        self.parameter_value = parameter_value
        self.out_of_memory = is_out_of_memory
        self.cases = [] if cases is None else cases

    # Check if any case has a measurement with the given name
    def has_measurement(self, name: str) -> bool:
        return any(case.find_measurement(name) is not None for case in self.cases)

    # Return the number of samples for a given measurement name
    def get_sample_count(self, name: str) -> int:
        return len(self._statistical_values(name))

    # Calculate the mean of a given measurement name across all cases
    def mean(self, name: str) -> float:
        return float(np.mean(self._statistical_values(name)))

    # Calculate the confidence interval of a given measurement name across all cases
    def confidence_interval(self, name: str) -> float:
        values = self._statistical_values(name)

        if len(values) == 1:
            return 0.0

        return float(stats.t.ppf(0.975, len(values) - 1) * stats.sem(values))

    # Calculate median of a given measurement name across all cases
    def median(self, name: str) -> float:
        return float(np.median(self._statistical_values(name)))

    # Calculate the minimum of a given measurement name across all cases
    def minimum(self, name: str) -> float:
        return min(self._statistical_values(name))

    # Calculate the maximum of a given measurement name across all cases
    def maximum(self, name: str) -> float:
        return max(self._statistical_values(name))

    # Calculate the first quartile of a given measurement name across all cases
    def first_quartile(self, name: str) -> float:
        return float(np.quantile(self._statistical_values(name), 0.25, method="linear"))

    # Calculate the third quartile of a given measurement name across all cases
    def third_quartile(self, name: str) -> float:
        return float(np.quantile(self._statistical_values(name), 0.75, method="linear"))

    # Calculate the interquartile range of a given measurement name across all cases
    def iqr(self, name: str) -> float:
        return self.third_quartile(name) - self.first_quartile(name)

    # Total number of iterations across all cases
    @property
    def iterations(self) -> int:
        return sum(case.iterations for case in self.cases)

    # Check if any case has experienced throttling
    @property
    def throttled(self) -> bool:
        if self.out_of_memory:
            self._reject_statistical_access()

        return self.has_measurement(THROTTLED) and self.maximum(THROTTLED) > 0

    # Raise an error if statistical access is attempted on an out-of-memory case
    def _statistical_values(self, name: str) -> list[float]:
        if self.out_of_memory:
            self._reject_statistical_access()

        values = []

        for case in self.cases:
            measurement = case.find_measurement(name)
            if measurement is not None:
                values.append(measurement.value)

        return values

    def _reject_statistical_access(self) -> None:
        raise ValueError(
            f"Cannot calculate statistics for out-of-memory case "
            f"{self.operation} {self.parameter}/{self.parameter_value}"
        )
