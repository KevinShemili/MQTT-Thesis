import math

import summary


# Result of fitting straight line to measured benchmark data
# 1. slope gives line's slope
# 2. intercept is value of fit at x = 0
# 3. r_squared indicates how closely the measured points follow the fit
# 4. slope_ci is CI half of calculated slope
class LinearRegression:
    def __init__(
        self,
        slope: float,
        intercept: float,
        r_squared: float,
        slope_ci: float,
    ) -> None:
        self.slope = slope
        self.intercept = intercept
        self.r_squared = r_squared
        self.slope_ci = slope_ci

    # Calculate y based on a given x value,
    # using the linear fit equation y = mx + b
    def calculate_y_based_on_x(self, x_value: float) -> float:
        return self.intercept + self.slope * x_value

    # Inverse of the above, x = (y - b) / m. Answers at which x the fitted line
    # reaches a given y, which is how a crossover against a flat cost is located
    def solve_x_for_y(self, y_value: float) -> float:
        return (y_value - self.intercept) / self.slope


def fit_linear_regression(
    x_values: list[float], y_values: list[float]
) -> LinearRegression:

    x_mean = summary.mean(x_values)
    y_mean = summary.mean(y_values)
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

    return LinearRegression(
        slope=slope,
        intercept=intercept,
        r_squared=r_squared,
        # CI (95%) = m ± t(0.975, n-2) × SE
        slope_ci=(
            summary.get_student_t_critical_95(point_count - 2) * slope_standard_error
        ),
    )
