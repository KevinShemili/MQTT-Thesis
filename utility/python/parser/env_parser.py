import os


def parse_int_env(name: str) -> int:
    return int(os.environ[name].strip())


def parse_int_list_env(name: str) -> list[int]:
    return [int(part.strip()) for part in os.environ[name].split(",")]
