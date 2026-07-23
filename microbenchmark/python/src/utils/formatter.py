def FormatByteSize(byteCount: int) -> str:

    # Display large table values in megabytes while preserving small size differences.
    if byteCount >= 1024 * 1024:
        megabytes: float = byteCount / float(1024 * 1024)
        formattedMegabytes: str = f"{megabytes:.4f}".rstrip("0").rstrip(".")
        return f"{formattedMegabytes} MB"

    # Display medium table values in kilobytes.
    if byteCount >= 1024:
        kilobytes: float = byteCount / float(1024)
        formattedKilobytes: str = f"{kilobytes:.2f}".rstrip("0").rstrip(".")
        return f"{formattedKilobytes} KB"

    return f"{byteCount} B"
