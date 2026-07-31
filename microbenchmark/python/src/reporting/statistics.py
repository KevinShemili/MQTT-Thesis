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


# Result of fitting a straight line to measured benchmark data
# 1. slope describes how much the measured value changes for every one-unit increase in x
# 2. intercept is the fitted value at x = 0
# 3. r_squared indicates how closely the measured points follow the fitted linear relationship
# 4. slope_ci is the 95% confidence-interval half-width for the calculated slope
@dataclass(frozen=True)
class LinearFit:
    slope: float
    intercept: float
    r_squared: float
    slope_ci: float

    # Value predicted by the fitted line at the given x
    def predict(self, x_value: float) -> float:
        return self.intercept + self.slope * x_value


def get_student_t_critical_95(degrees_of_freedom: int) -> float:
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
    mean_value = mean(values)

    # Σ(xᵢ - x̄)²
    squared_deviation_sum = sum((value - mean_value) ** 2 for value in values)

    # s² = Σ(xᵢ - x̄)² / (n - 1)
    variance = squared_deviation_sum / (value_count - 1)

    # s = √s²
    standard_deviation = math.sqrt(variance)

    # SE = s / √n
    standard_error = standard_deviation / math.sqrt(value_count)

    # CI (95%) = x̄ ± t(0.975, n-1) × (s / √n)
    ci_half = t_critical * standard_error

    return mean_value, ci_half


def fit_linear_regression(x_values: list[float], y_values: list[float]) -> LinearFit:

    x_mean = mean(x_values)
    y_mean = mean(y_values)
    point_count = len(x_values)

    # Σ(xᵢ - x̄)(yᵢ - ȳ)
    numerator = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values, strict=True)
    )

    # Σ(xᵢ - x̄)²
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    # m = Σ(xᵢ - x̄)(yᵢ - ȳ) / Σ(xᵢ - x̄)²
    slope = numerator / denominator

    # b = ȳ - mx̄
    intercept = y_mean - slope * x_mean

    # SSE = Σ[yᵢ - (mxᵢ + b)]²
    sum_squared_residuals = sum(
        (y - (slope * x + intercept)) ** 2
        for x, y in zip(x_values, y_values, strict=True)
    )

    # SST = Σ(yᵢ - ȳ)²
    sum_squared_total = sum((y - y_mean) ** 2 for y in y_values)

    # R² = 1 - (SSE / SST)
    r_squared = 1.0 - (sum_squared_residuals / sum_squared_total)

    # s² = SSE / (n - 2)
    residual_variance = sum_squared_residuals / (point_count - 2)

    # SE = √[s² / Σ(xᵢ - x̄)²]
    slope_standard_error = math.sqrt(residual_variance / denominator)

    return LinearFit(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        # CI (95%) = m ± t(0.975, n-2) × SE
        slope_ci=(get_student_t_critical_95(point_count - 2) * slope_standard_error),
    )
