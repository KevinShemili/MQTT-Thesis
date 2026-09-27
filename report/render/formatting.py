from report.analysis.shared.metrics import MEGABYTE

KILOBYTE = 1024


def format_byte_size(byte_count: int, compact: bool = False) -> str:
    if byte_count >= MEGABYTE:
        if compact:
            return f"{byte_count // MEGABYTE}MB"

        megabytes: str = f"{byte_count / MEGABYTE:.4f}".rstrip("0").rstrip(".")
        return f"{megabytes} MB"

    if byte_count >= KILOBYTE:
        if compact:
            return f"{byte_count // KILOBYTE}KB"

        kilobytes: str = f"{byte_count / KILOBYTE:.2f}".rstrip("0").rstrip(".")
        return f"{kilobytes} KB"

    if compact:
        return f"{byte_count}B"

    return f"{byte_count} B"


def format_mean_with_ci(
    mean_value: float,
    ci_half: float,
    decimals: int = 2,
    thousands: bool = True,
) -> str:
    grouping = "," if thousands else ""
    return f"{mean_value:{grouping}.{decimals}f} ± {ci_half:{grouping}.{decimals}f}"


def format_attribute_label(attribute_count: int) -> str:
    if attribute_count == 1:
        return "1 ATTRIBUTE"

    return f"{attribute_count} ATTRIBUTES"
