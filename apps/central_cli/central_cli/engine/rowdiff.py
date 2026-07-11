from __future__ import annotations


def restore_cursor_index(
    selected_key: str | None, new_keys: list[str], old_index: int
) -> int:
    """Hvor markøren skal stå efter en tabel-genopbygning.
    Markøren FØLGER den valgte key hvis den stadig findes; ellers bevares det
    gamle index, clampet til det nye række-antal. Tom tabel → 0."""
    if not new_keys:
        return 0
    if selected_key is not None and selected_key in new_keys:
        return new_keys.index(selected_key)
    return min(max(old_index, 0), len(new_keys) - 1)
