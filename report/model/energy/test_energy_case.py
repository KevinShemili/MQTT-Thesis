from report.model.energy.energy_case import EnergyCase, EnergySample


def test_energy_case_adds_and_finds_measurement():

    # Arrange
    case = EnergyCase(1)

    # Act
    case.add_measurement("ns/op", 123.0)

    # Assert
    assert case.find_measurement("ns/op") == 123.0


def test_energy_case_adds_sample():

    # Arrange
    case = EnergyCase(1)
    sample = EnergySample(
        elapsed_s=1.0,
        voltage_v=5.0,
        current_a=0.2,
        power_w=1.0,
    )

    # Act
    case.add_sample(sample)

    # Assert
    assert case.samples == [sample]
