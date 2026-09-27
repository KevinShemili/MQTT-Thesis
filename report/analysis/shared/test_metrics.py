from types import SimpleNamespace

from report.analysis.shared.metrics import (
    collect_energy_throttle_flags,
    collect_timing_throttle_flags,
    to_megabytes,
    to_microjoules,
    to_microseconds,
)
from report.model.energy.energy_case import THROTTLED as ENERGY_THROTTLED
from report.model.timing.timing_case import THROTTLED as TIMING_THROTTLED


def test_collect_timing_throttle_flags():

    # Arrange
    aggregations = [
        SimpleNamespace(
            cases=[
                SimpleNamespace(measurements={TIMING_THROTTLED: 0}),
                SimpleNamespace(measurements={TIMING_THROTTLED: 0}),
            ]
        ),
        SimpleNamespace(
            cases=[
                SimpleNamespace(measurements={TIMING_THROTTLED: 0}),
                SimpleNamespace(measurements={TIMING_THROTTLED: 1}),
            ]
        ),
    ]

    # Act
    result = collect_timing_throttle_flags(aggregations)

    # Assert
    assert result == [False, True]


def test_collect_energy_throttle_flags():

    # Arrange
    aggregations = [
        SimpleNamespace(
            cases=[
                SimpleNamespace(measurements={ENERGY_THROTTLED: 0}),
                SimpleNamespace(measurements={ENERGY_THROTTLED: 0}),
            ]
        ),
        SimpleNamespace(
            cases=[
                SimpleNamespace(measurements={ENERGY_THROTTLED: 1}),
                SimpleNamespace(measurements={ENERGY_THROTTLED: 0}),
            ]
        ),
    ]

    # Act
    result = collect_energy_throttle_flags(aggregations)

    # Assert
    assert result == [False, True]


def test_to_microseconds():

    # Arrange
    values = [1_000.0, 2_500.0, 10_000.0]

    # Act
    result = to_microseconds(values)

    # Assert
    assert result == [1.0, 2.5, 10.0]


def test_to_microjoules():

    # Arrange
    values = [0.000001, 0.0000025, 0.001]

    # Act
    result = to_microjoules(values)

    # Assert
    assert result == [1.0, 2.5, 1000.0]


def test_to_megabytes():

    # Arrange
    values = [
        1_048_576.0,
        2_097_152.0,
        524_288.0,
    ]

    # Act
    result = to_megabytes(values)

    # Assert
    assert result == [1.0, 2.0, 0.5]
