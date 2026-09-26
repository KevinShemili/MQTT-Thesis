import sys
from pathlib import Path

test_directory = Path(__file__).resolve().parent
sys.path.remove(str(test_directory))
sys.path.insert(0, str(test_directory.parents[2]))

from report.analysis.shared.statistics import (
    _joules_per_operation,
    energy_statistics,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import NS_PER_OP, EnergyCase, EnergySample


def test_joules_per_operation_uses_measurement_window():

    # Arrange
    # Measure from 2 seconds (inclusive) to 5 seconds (exclusive)
    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
        warmup_duration=2.0,
        measurement_duration=3.0,
    )

    case = EnergyCase()
    case.add_measurement(NS_PER_OP, 1_000_000_000)

    case.add_sample(
        EnergySample(elapsed_s=1.0, voltage_v=0.0, current_a=0.0, power_w=100.0)
    )
    case.add_sample(
        EnergySample(elapsed_s=2.0, voltage_v=0.0, current_a=0.0, power_w=6.0)
    )
    case.add_sample(
        EnergySample(elapsed_s=4.0, voltage_v=0.0, current_a=0.0, power_w=10.0)
    )
    case.add_sample(
        EnergySample(elapsed_s=5.0, voltage_v=0.0, current_a=0.0, power_w=100.0)
    )

    aggregation.cases = [case]

    # Act
    values = _joules_per_operation(
        aggregation,
        idle_power_w=2.0,
    )

    # Assert
    # Included power samples: (6 + 10) / 2 = 8 W
    # Energy per operation: (8 - 2) W * 1 s = 6 J
    assert values == [6.0]


def test_energy_statistics_uses_mean_of_baseline_cases():

    # Arrange
    # First baseline run has mean power 3 W
    first_baseline_case = EnergyCase()
    first_baseline_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=2.0)
    )
    first_baseline_case.add_sample(
        EnergySample(elapsed_s=1.0, voltage_v=0.0, current_a=0.0, power_w=4.0)
    )

    # Second baseline run has mean power 7 W
    second_baseline_case = EnergyCase()
    second_baseline_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=7.0)
    )

    baseline_cases = [
        first_baseline_case,
        second_baseline_case,
    ]

    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
        warmup_duration=0.0,
        measurement_duration=1.0,
    )

    measured_case = EnergyCase()
    measured_case.add_measurement(NS_PER_OP, 1_000_000_000)
    measured_case.add_sample(
        EnergySample(elapsed_s=0.0, voltage_v=0.0, current_a=0.0, power_w=9.0)
    )

    aggregation.cases = [measured_case]

    # Act
    means, _ = energy_statistics(
        [aggregation],
        baseline_cases,
    )

    # Assert:
    # Baseline run means: (3 + 7) / 2 = 5 W
    # Energy per operation: (9 - 5) W * 1 s = 4 J
    assert means == [4.0]
