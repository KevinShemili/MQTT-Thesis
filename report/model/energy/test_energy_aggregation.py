from report.model.energy.energy_aggregation import EnergyAggregation
from report.model.energy.energy_case import EnergyCase


def test_energy_aggregation_finds_case_by_run():

    # Arrange
    aggregation = EnergyAggregation(
        algorithm="AES-GCM",
        operation="Encrypt",
        parameter="payload_size",
        parameter_value=16,
    )

    first_case = EnergyCase(1)
    second_case = EnergyCase(2)

    aggregation.cases = [
        first_case,
        second_case,
    ]

    # Act
    result = aggregation.find_case(2)

    # Assert
    assert result is second_case
