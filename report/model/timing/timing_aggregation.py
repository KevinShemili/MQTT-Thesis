from .timing_case import TimingCase


# Groups independent timing benchmark runs
class TimingAggregation:

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
        self.cases: list[TimingCase] = []
