from .macro_case import MacroCase


# Groups repeated MQTT workloads for one algorithm and payload size
class MacroAggregation:

    def __init__(
        self,
        algorithm: str,
        payload_size: int,
    ):
        self.algorithm = algorithm
        self.payload_size = payload_size
        self.cases: list[MacroCase] = []

    # Find one recorded repetition
    def find_case(self, repetition: int) -> MacroCase | None:

        for case in self.cases:
            if case.repetition == repetition:
                return case

        return None
