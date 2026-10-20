def to_int(value, default, low, high):
    """Ubah input form jadi integer yang aman (dibatasi low..high), atau default kalau bukan angka."""
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError):
        return default
