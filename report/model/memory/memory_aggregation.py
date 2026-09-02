from .memory_case import MemoryCase


# Groups independent memory benchmark runs
class MemoryAggregation:

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
        self.cases: list[MemoryCase] = []
