import math


def GetStudentTCriticalValue95(degreesOfFreedom: int) -> float:

    studentTCriticalValues: dict[int, float] = {
        1: 12.71,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        11: 2.201,
        12: 2.179,
        13: 2.160,
        14: 2.145,
        15: 2.131,
    }

    if degreesOfFreedom not in studentTCriticalValues:
        raise ValueError(f"Unsupported degrees of freedom: {degreesOfFreedom}")

    return studentTCriticalValues[degreesOfFreedom]


def Mean(values: list[float] | list[int]) -> float:
    # Average repeated measurements for one benchmark case.
    return sum(values) / len(values)


def MeanAndConfidenceInterval(
    values: list[float],
    tCriticalValue: float,
) -> tuple[float, float]:

    valueCount: int = len(values)

    # Mean gives the central estimate across repeated runs.
    mean: float = Mean(values)

    # Sum squared deviations to measure run-to-run spread.
    squaredDeviationSum: float = 0.0

    for value in values:
        squaredDeviationSum += (value - mean) ** 2

    # Sample variance uses n - 1 because runs are samples, not the full population.
    variance: float = squaredDeviationSum / (valueCount - 1)

    # Standard deviation describes spread between independent runs.
    standardDeviation: float = math.sqrt(variance)

    # Standard error describes uncertainty around the mean.
    standardError: float = standardDeviation / math.sqrt(valueCount)

    # CI half-width scales standard error by the chosen Student t value.
    ciHalf: float = tCriticalValue * standardError

    return mean, ciHalf


def FitLinearRegression(
    xValues: list[float], yValues: list[float]
) -> tuple[float, float, float]:

    xMean: float = Mean(xValues)
    yMean: float = Mean(yValues)

    numerator: float = 0.0
    denominator: float = 0.0

    # Ordinary least squares: slope = covariance(x, y) / variance(x).
    for index in range(len(xValues)):
        numerator += (xValues[index] - xMean) * (yValues[index] - yMean)
        denominator += (xValues[index] - xMean) ** 2

    slope: float = numerator / denominator
    intercept: float = yMean - slope * xMean

    # R-squared: how much of the spread in y is explained by the fitted line.
    sumSquaredResiduals: float = 0.0
    sumSquaredTotal: float = 0.0

    for index in range(len(xValues)):
        predictedY: float = slope * xValues[index] + intercept
        sumSquaredResiduals += (yValues[index] - predictedY) ** 2
        sumSquaredTotal += (yValues[index] - yMean) ** 2

    rSquared: float = 1.0 - (sumSquaredResiduals / sumSquaredTotal)

    # Residual variance uses n - 2 degrees of freedom: two parameters (slope, intercept) are fit.
    pointCount: int = len(xValues)
    residualVariance: float = sumSquaredResiduals / (pointCount - 2)

    # Standard error of the slope, from the standard OLS formula.
    slopeStandardError: float = math.sqrt(residualVariance / denominator)

    return slope, rSquared, slopeStandardError


def ComputeSlopeConfidenceInterval(slopeStandardError: float, pointCount: int) -> float:

    # Same t-distribution as the point-wise CIs, but df here is sweep points minus 2 parameters.
    tCriticalValue: float = GetStudentTCriticalValue95(pointCount - 2)

    return tCriticalValue * slopeStandardError
