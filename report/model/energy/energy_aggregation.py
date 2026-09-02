from .energy_case import EnergyCase


# Groups independent energy benchmark runs
class EnergyAggregation:

    def __init__(
        self,
        algorithm: str,
        operation: str,
        parameter: str,
        parameter_value: int,
        warmup_duration: float,
        measurement_duration: float,
    ):
        self.algorithm = algorithm
        self.operation = operation
        self.parameter = parameter
        self.parameter_value = parameter_value
        self.warmup_duration = warmup_duration
        self.measurement_duration = measurement_duration
        self.cases: list[EnergyCase] = []
