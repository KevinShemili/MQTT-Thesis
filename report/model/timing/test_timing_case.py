from report.model.timing.timing_case import TimingCase


def test_timing_case_adds_and_finds_measurement():

    # Arrange
    case = TimingCase(1)

    # Act
    case.add_measurement("ns/op", 123.0)

    # Assert
    assert case.find_measurement("ns/op") == 123.0
