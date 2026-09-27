MAX_PAGE_SIZE = 100


def clamp_page(skip: int, limit: int, max_size: int = MAX_PAGE_SIZE) -> tuple[int, int]:
    skip = max(0, int(skip or 0))
    limit = min(max(1, int(limit or 1)), max_size)
    return skip, limit


def ilike_pattern(search: str) -> str | None:
    raw = (search or "").strip()
    if not raw:
        return None
    escaped = raw.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
