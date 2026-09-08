# Different types of measurements collected by the Go timing benchmarks
NS_PER_OP = "ns/op"
MB_PER_SECOND = "MB/s"
ADDITIONAL_OVERHEAD_BYTES = "additional_overhead_bytes"
ENVELOPE_BYTES = "envelope_bytes"
RAW_BYTES = "raw_bytes"
CIPHERTEXT_BYTES = "ciphertext_bytes"
TOTAL_CIPHERTEXT_BYTES = "total_ciphertext_bytes"
STORED_KEY_BYTES = "stored_key_bytes"
THROTTLED = "throttled"


# Single repetition (1 out of N in -test.count = N)
class TimingCase:

    def __init__(self, iterations: int):
        self.iterations = iterations
        self.measurements: dict[str, float] = {}

    # Add a measured value to this case
    def add_measurement(self, name: str, value: float) -> None:
        self.measurements[name] = value

    # Find a measured value by name
    def find_measurement(self, name: str) -> float | None:
        return self.measurements.get(name)
