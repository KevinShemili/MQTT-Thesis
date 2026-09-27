import sys
from pathlib import Path

test_directory = Path(__file__).resolve().parent
sys.path.remove(str(test_directory))
sys.path.insert(0, str(test_directory.parents[2]))

from report.analysis.shared.statistics import (
    _joules_per_operation,
    energy_statistics,
    macro_cycle_statistics,
    macro_latency_statistics,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import EnergyCase, EnergySample
from report.model.macro.macro_aggregation import MacroAggregation
from report.model.macro.macro_case import MacroCase
from report.model.timing.timing_aggregation import TimingAggregation
from report.model.timing.timing_case import NS_PER_OP, TimingCase


def test_joules_per_operation_uses_mean_load_power():

    # Arrange
    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
    )

    case = EnergyCase(1)
    case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=4.0)
    )
    case.add_sample(
        EnergySample(elapsed_s=1.0, voltage_v=0.0, current_a=0.0, power_w=8.0)
    )
    aggregation.cases.append(case)

    # Act
    values = _joules_per_operation(aggregation, idle_power_w=2.0, mean_latency_s=0.5)

    # Assert
    # Mean load power = 6 W
    # Power above idle = 6 W - 2 W = 4 W
    # Energy = 4 W * 0.5 s = 2 J

    assert values == [2.0]


def test_energy_statistics_uses_matching_timing_and_baseline_power():

    # Arrange
    first_baseline_case = EnergyCase(1)
    first_baseline_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=2.0)
    )

    second_baseline_case = EnergyCase(2)
    second_baseline_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=6.0)
    )

    baseline_cases = [
        first_baseline_case,
        second_baseline_case,
    ]

    energy_aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
    )

    energy_case = EnergyCase(1)
    energy_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=8.0)
    )
    energy_aggregation.cases.append(energy_case)

    unrelated_timing = TimingAggregation(
        "ASCON",
        "Encrypt",
        "payload_size",
        16,
    )
    unrelated_timing_case = TimingCase(1)
    unrelated_timing_case.add_measurement(NS_PER_OP, 1_000_000_000)
    unrelated_timing.cases.append(unrelated_timing_case)

    matching_timing = TimingAggregation(
        "AES-GCM",
        "Encrypt",
        "payload_size",
        16,
    )
    matching_timing_case = TimingCase(1)
    matching_timing_case.add_measurement(NS_PER_OP, 500_000_000)
    matching_timing.cases.append(matching_timing_case)

    # Act
    means, confidence_intervals = energy_statistics(
        [energy_aggregation], baseline_cases, [unrelated_timing, matching_timing]
    )

    # Assert
    # Mean idle power = 4 W
    # Matching timing latency = 0.5 s
    # Energy = (8 W - 4 W) * 0.5 s = 2 J

    assert means == [2.0]
    assert confidence_intervals == [0.0]


def test_macro_latency_statistics_averages_messages_within_repetition():

    # Arrange
    aggregation = MacroAggregation("MQTT-TLS", 256)

    case = MacroCase(1)
    case.publisher_timestamps = {
        "message-1": 100,
        "message-2": 200,
    }
    case.subscriber_timestamps = {
        "message-1": 104,
        "message-2": 206,
    }

    aggregation.cases.append(case)

    # Act
    means, confidence_intervals = macro_latency_statistics([aggregation])

    # Assert
    # Message latencies are 4 ns and 6 ns -> Repetition mean = 5 ns

    assert means == [5.0]
    assert confidence_intervals == [0.0]


def test_macro_cycle_statistics_separates_publisher_and_subscriber_cycles():

    # Arrange
    aggregation = MacroAggregation("MQTT-TLS", 256)

    case = MacroCase(1)
    case.publisher_cycles = 100
    case.subscriber_cycles = 200
    aggregation.cases.append(case)

    expected = {
        "publisher": ([100.0], [0.0]),
        "subscriber": ([200.0], [0.0]),
    }

    # Act
    result = macro_cycle_statistics([aggregation])

    # Assert
    assert result == expected
