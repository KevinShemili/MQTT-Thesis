NS_PER_OP = "ns/op"
THROTTLED = "throttled"


# One UM24C power sample
class EnergySample:

    def __init__(
        self,
        elapsed_s: float,
        voltage_v: float,
        current_a: float,
        power_w: float,
    ):
        self.elapsed_s = elapsed_s
        self.voltage_v = voltage_v
        self.current_a = current_a
        self.power_w = power_w


# Single repetition (1 out of N in -test.count = N)
class EnergyCase:

    def __init__(self):
        self.measurements: dict[str, float] = {}
        self.samples: list[EnergySample] = []

    # Add a scalar measurement belonging to this run
    def add_measurement(self, name: str, value: float) -> None:
        self.measurements[name] = value

    # Find a scalar measurement by name
    def find_measurement(self, name: str) -> float | None:
        return self.measurements.get(name)

    # Add one UM24C sample
    def add_sample(self, sample: EnergySample) -> None:
        self.samples.append(sample)
