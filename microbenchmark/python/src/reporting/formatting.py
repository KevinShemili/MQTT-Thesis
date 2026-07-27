KILOBYTE = 1024
MEGABYTE = 1024 * 1024


# Convert raw byte count into a human-readable size using B, KB, or MB ex. 1536 -> "1.5 KB"
# Compact form removes decimals and spaces ex. 1536 -> "1KB"
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


# Convert raw byte count into its compact form ex. 4194304 -> "4MB",
# intented for use in axis tick labels where space is limited
def format_byte_size_compact(byte_count: int) -> str:
    return format_byte_size(byte_count, compact=True)


# From something like: mean=125272.17, ci=320.5 to: "125,272.17 ± 320.50"
def format_mean_with_ci(
    mean_value: float,
    ci_half: float,
    decimals: int = 2,
    thousands: bool = True,
) -> str:
    grouping = "," if thousands else ""
    return f"{mean_value:{grouping}.{decimals}f} ± {ci_half:{grouping}.{decimals}f}"
