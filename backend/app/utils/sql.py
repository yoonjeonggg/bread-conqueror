"""Small SQL helpers shared by routers."""

LIKE_ESCAPE = "\\"


def contains_pattern(term: str) -> str:
    """LIKE pattern matching ``term`` literally anywhere in a column.

    User input is a search term, not a pattern: ``%``/``_`` are escaped so
    they can't turn into wildcards. Pair with ``escape=LIKE_ESCAPE``.
    """
    escaped = (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", r"\%").replace("_", r"\_")
    )
    return f"%{escaped}%"
