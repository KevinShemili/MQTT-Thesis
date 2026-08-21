import math

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


def get_student_t_critical_95(degrees_of_freedom: int) -> float:
    if degrees_of_freedom not in STUDENT_T_CRITICAL_95:
        raise ValueError(f"Unsupported degrees of freedom: {degrees_of_freedom}")

    return STUDENT_T_CRITICAL_95[degrees_of_freedom]


def mean(values: list[float] | list[int]) -> float:
    return sum(values) / len(values)


# Value below which the given fraction of the samples fall, ex. fraction=0.25
# gives the first quartile. The requested rank rarely lands exactly on a sample,
# so the two samples surrounding it are interpolated linearly
def percentile(values: list[float], fraction: float) -> float:

    ordered = sorted(values)

    # rank = (n - 1) × fraction, position of the wanted value in the ordered samples
    rank = (len(ordered) - 1) * fraction

    lower_index = math.floor(rank)
    upper_index = math.ceil(rank)

    if lower_index == upper_index:
        return ordered[lower_index]

    # Weight of the upper sample, which is how far the rank sits past the lower one
    weight = rank - lower_index

    # x = x_lower + weight × (x_upper - x_lower)
    return ordered[lower_index] + weight * (ordered[upper_index] - ordered[lower_index])


def median(values: list[float]) -> float:
    return percentile(values, 0.5)


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
