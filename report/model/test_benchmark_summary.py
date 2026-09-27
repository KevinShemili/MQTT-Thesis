from report.model.benchmark_summary import BenchmarkSummary
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.macro.macro_aggregation import MacroAggregation
from report.model.memory.memory_aggregation import MemoryAggregation
from report.model.timing.timing_aggregation import TimingAggregation


def test_benchmark_summary_finds_timing_aggregation():

    # Arrange
    summary = BenchmarkSummary()

    expected = TimingAggregation("AES-GCM", "Encrypt", "payload_size", 16)

    summary.timing_aggregations = [
        TimingAggregation("ASCON", "Encrypt", "payload_size", 16),
        expected,
    ]

    # Act
    result = summary.find_timing_aggregation("AES-GCM", "Encrypt", "payload_size", 16)

    # Assert
    assert result is expected


def test_benchmark_summary_finds_memory_aggregation():

    # Arrange
    summary = BenchmarkSummary()

    expected = MemoryAggregation("AES-GCM", "Encrypt", "payload_size", 16)

    summary.memory_aggregations = [
        MemoryAggregation("ASCON", "Encrypt", "payload_size", 16),
        expected,
    ]

    # Act
    result = summary.find_memory_aggregation("AES-GCM", "Encrypt", "payload_size", 16)

    # Assert
    assert result is expected


def test_benchmark_summary_finds_energy_aggregation():

    # Arrange
    summary = BenchmarkSummary()

    expected = EnergyAggregation("AES-GCM", "Encrypt", "payload_size", 16)

    summary.energy_aggregations = [
        EnergyAggregation("ASCON", "Encrypt", "payload_size", 16),
        expected,
    ]

    # Act
    result = summary.find_energy_aggregation("AES-GCM", "Encrypt", "payload_size", 16)

    # Assert
    assert result is expected


def test_benchmark_summary_finds_macro_aggregation():

    # Arrange
    summary = BenchmarkSummary()

    expected = MacroAggregation("MQTT-TLS", 256)

    summary.macro_aggregations = [
        MacroAggregation("MQTT-TLS", 128),
        expected,
    ]

    # Act
    result = summary.find_macro_aggregation("MQTT-TLS", 256)

    # Assert
    assert result is expected
