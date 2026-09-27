from report.model.memory.memory_case import MemoryCase


def test_memory_case_adds_and_finds_measurement():

    # Arrange
    case = MemoryCase(1)

    # Act
    case.add_measurement("peak_rss_bytes", 1024.0)

    # Assert
    assert case.find_measurement("peak_rss_bytes") == 1024.0
