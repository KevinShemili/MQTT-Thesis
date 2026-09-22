from report.analysis.shared.statistics import (
    _joules_per_operation,
    energy_statistics,
)
from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import NS_PER_OP, EnergyCase, EnergySample


def build_case(
    samples: list[tuple[float, float]],
    ns_per_op: float | None = None,
) -> EnergyCase:

    case = EnergyCase()

    if ns_per_op is not None:
        case.add_measurement(NS_PER_OP, ns_per_op)

    for elapsed_s, power_w in samples:
        case.add_sample(
            EnergySample(
                elapsed_s=elapsed_s,
                voltage_v=0.0,
                current_a=0.0,
                power_w=power_w,
            )
        )

    return case


def test_joules_per_operation_uses_measurement_window():

    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
        warmup_duration=2.0,
        measurement_duration=3.0,
    )

    aggregation.cases = [
        build_case(
            ns_per_op=1_000_000_000,
            samples=[
                (1.0, 100.0),  # Before measurement: ignored
                (2.0, 6.0),  # Included
                (4.0, 10.0),  # Included
                (5.0, 100.0),  # End of measurement: ignored
            ],
        )
    ]

    values = _joules_per_operation(
        aggregation,
        idle_power_w=2.0,
    )

    # Measurement window is 3 seconds -> Average power is (6 + 10) / 2 = 8 W
    # Idle power is 2 W, so the net power is 6 W -> number of operations is 1 -> Energy per operation is 6 J
    assert values == [6.0]


def test_energy_statistics_uses_mean_of_baseline_cases():

    baseline_cases = [
        build_case(samples=[(0.0, 2.0), (1.0, 4.0)]),  # Mean = 3 W
        build_case(samples=[(0.0, 7.0)]),  # Mean = 7 W
    ]

    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
        warmup_duration=0.0,
        measurement_duration=1.0,
    )

    aggregation.cases = [
        build_case(
            ns_per_op=1_000_000_000,
            samples=[
                (0.0, 9.0),
            ],
        )
    ]

    means, _ = energy_statistics(
        [aggregation],
        baseline_cases,
    )

    # Mean of the baseline cases is (3 + 7) / 2 = 5 W -> net power is 9 - 5 = 4 W
    # Number of operations is 1 -> Energy per operation is 4 J
    assert means == [4.0]
