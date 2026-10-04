import pytest

from utility.python.parser.env_parser import (
    parse_int_env,
    parse_int_list_env,
)


def test_parse_int_env(monkeypatch):

    # Arrange
    monkeypatch.setenv("TEST_INT", " 42 ")

    # Act
    result = parse_int_env("TEST_INT")

    # Assert
    assert result == 42


def test_parse_int_env_raises_for_invalid_value(monkeypatch):

    # Arrange
    monkeypatch.setenv("TEST_INT", "invalid")

    # Act & Assert
    with pytest.raises(ValueError):
        parse_int_env("TEST_INT")


def test_parse_int_list_env(monkeypatch):

    # Arrange
    monkeypatch.setenv("TEST_INT_LIST", "16, 256, 4096")

    # Act
    result = parse_int_list_env("TEST_INT_LIST")

    # Assert
    assert result == [16, 256, 4096]


def test_parse_int_list_env_raises_for_invalid_value(monkeypatch):

    # Arrange
    monkeypatch.setenv("TEST_INT_LIST", "16, invalid, 4096")

    # Act & Assert
    with pytest.raises(ValueError):
        parse_int_list_env("TEST_INT_LIST")
