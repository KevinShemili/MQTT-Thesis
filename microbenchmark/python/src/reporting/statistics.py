import math
from dataclasses import dataclass

STUDENT_T_CRITICAL_95: dict[int, float] = {
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


@dataclass(frozen=True)
class LinearFit:
    slope: float
    r_squared: float
    slope_ci: float


def student_t_critical_95(degrees_of_freedom: int) -> float:
    if degrees_of_freedom not in STUDENT_T_CRITICAL_95:
        raise ValueError(f"Unsupported degrees of freedom: {degrees_of_freedom}")

    return STUDENT_T_CRITICAL_95[degrees_of_freedom]


def mean(values: list[float] | list[int]) -> float:
    return sum(values) / len(values)


def mean_and_confidence_interval(
    values: list[float],
    t_critical: float,
) -> tuple[float, float]:

    value_count = len(values)

    # Mean gives the central estimate across repeated runs.
    mean_value = mean(values)

    # Sum squared deviations to measure run-to-run spread.
    squared_deviation_sum = sum((value - mean_value) ** 2 for value in values)

    # Sample variance uses n - 1 because runs are samples, not the full population.
    variance = squared_deviation_sum / (value_count - 1)

    # Standard deviation describes spread between independent runs.
    standard_deviation = math.sqrt(variance)

    # Standard error describes uncertainty around the mean.
    standard_error = standard_deviation / math.sqrt(value_count)

    # CI half-width scales standard error by the chosen Student t value.
    ci_half = t_critical * standard_error

    return mean_value, ci_half


def fit_linear_regression(x_values: list[float], y_values: list[float]) -> LinearFit:

    x_mean = mean(x_values)
    y_mean = mean(y_values)

    # Ordinary least squares: slope = covariance(x, y) / variance(x).
    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)
    )
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    # R-squared: how much of the spread in y is explained by the fitted line.
    sum_squared_residuals = sum(
        (y - (slope * x + intercept)) ** 2
        for x, y in zip(x_values, y_values, strict=True)
    )
    sum_squared_total = sum((y - y_mean) ** 2 for y in y_values)

    r_squared = 1.0 - (sum_squared_residuals / sum_squared_total)

    # Residual variance uses n - 2 degrees of freedom: two parameters (slope, intercept) are fit.
    point_count = len(x_values)
    residual_variance = sum_squared_residuals / (point_count - 2)

    # Standard error of the slope, from the standard OLS formula.
    slope_standard_error = math.sqrt(residual_variance / denominator)

    return LinearFit(
        slope=slope,
        r_squared=r_squared,
        slope_ci=slope_confidence_interval(slope_standard_error, point_count),
    )


def slope_confidence_interval(slope_standard_error: float, point_count: int) -> float:
    return student_t_critical_95(point_count - 2) * slope_standard_error
