import os


def ParseIntListFromEnv(envVarName: str) -> list[int]:
    rawValue: str = os.environ[envVarName]
    rawParts: list[str] = rawValue.split(",")

    values: list[int] = []
    for part in rawParts:
        values.append(int(part.strip()))

    return values


def ParseIntFromEnv(envVarName: str) -> int:
    rawValue: str = os.environ[envVarName]
    return int(rawValue.strip())
