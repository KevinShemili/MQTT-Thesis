from report.model.macro.macro_aggregation import MacroAggregation
from report.model.macro.macro_case import MacroCase


def test_macro_aggregation_finds_case_by_repetition():

    # Arrange
    aggregation = MacroAggregation(
        algorithm="MQTT-TLS",
        payload_size=256,
    )

    first_case = MacroCase(1)
    second_case = MacroCase(2)

    aggregation.cases = [
        first_case,
        second_case,
    ]

    # Act
    result = aggregation.find_case(2)

    # Assert
    assert result is second_case
