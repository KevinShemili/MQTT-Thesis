from __future__ import annotations

# Different types of measurements collected by the Go benchmarks
NS_PER_OP = "ns/op"
MB_PER_SECOND = "MB/s"
additional_overhead_bytes = "additional_overhead_bytes"
ENVELOPE_BYTES = "envelope_bytes/op"
RAW_BYTES = "raw_bytes/op"
CIPHERTEXT_BYTES = "ciphertext_bytes"
TOTAL_CIPHERTEXT_BYTES = "total_ciphertext_bytes"
STORED_KEY_BYTES = "stored_key_bytes"
PEAK_RSS_BYTES = "peak_rss_bytes"
THROTTLED = "throttled"


# One specific measurement & its value
class Measurement:

    def __init__(self, name: str, value: float) -> None:
        self.name = name  # "ns/op"
        self.value = value  # 123.4
