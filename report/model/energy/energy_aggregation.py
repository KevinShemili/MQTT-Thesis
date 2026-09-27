from .energy_case import EnergyCase


# Groups independent energy benchmark runs
class EnergyAggregation:

    def __init__(
        self,
        algorithm: str,
        operation: str,
        parameter: str,
        parameter_value: int,
    ):
        self.algorithm = algorithm
        self.operation = operation
        self.parameter = parameter
        self.parameter_value = parameter_value
        self.cases: list[EnergyCase] = []

    # Find one recorded repetition
    def find_case(self, run: int) -> EnergyCase | None:

        for case in self.cases:
            if case.run == run:
                return case

        return None
