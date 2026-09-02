PEAK_RSS_BYTES = "peak_rss_bytes"


# Single repetition (1 out of N independent memory processes)
class MemoryCase:

    def __init__(self, iterations: int):
        self.iterations = iterations
        self.measurements: dict[str, float] = {}

    # Add a measured value to this case
    def add_measurement(self, name: str, value: float) -> None:
        self.measurements[name] = value

    # Find a measured value by name
    def find_measurement(self, name: str) -> float | None:
        return self.measurements.get(name)
