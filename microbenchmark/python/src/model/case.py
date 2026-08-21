from __future__ import annotations
from model.measurement import Measurement


# Single repetition (1 out of N in -test.count = N)
class Case:

    def __init__(
        self,
        iterations: int,  # Total iterations
        measurements: list[Measurement],  # List of measured values
    ) -> None:
        self.iterations = iterations
        self.measurements = measurements

    def find_measurement(self, name: str) -> Measurement | None:
        for measurement in self.measurements:
            if measurement.name == name:
                return measurement

        return None
