KIBIBYTE = 1024
MEBIBYTE = 1024 * 1024


def format_byte_size(byte_count: int) -> str:
    if byte_count >= MEBIBYTE:
        megabytes = f"{byte_count / float(MEBIBYTE):.4f}".rstrip("0").rstrip(".")
        return f"{megabytes} MB"

    if byte_count >= KIBIBYTE:
        kilobytes = f"{byte_count / float(KIBIBYTE):.2f}".rstrip("0").rstrip(".")
        return f"{kilobytes} KB"

    return f"{byte_count} B"


def format_compact_byte_size(byte_count: int) -> str:
    if byte_count >= MEBIBYTE:
        return f"{byte_count // MEBIBYTE}MB"

    if byte_count >= KIBIBYTE:
        return f"{byte_count // KIBIBYTE}KB"

    return f"{byte_count}B"


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
