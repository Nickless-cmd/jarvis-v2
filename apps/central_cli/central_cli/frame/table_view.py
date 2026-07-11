from __future__ import annotations

from textual.widgets import DataTable

from central_cli.engine.rowdiff import restore_cursor_index


class CursorStableTable(DataTable):
    """DataTable hvor markør + valgt element BEVARES på tværs af data-opdateringer.
    Vi fanger den valgte row-KEY, genopbygger rækkerne, og flytter markøren tilbage
    til samme key (rowdiff.restore_cursor_index). Løser markør-hop ved refresh."""

    def __init__(self, *columns: tuple[str, int], **kwargs) -> None:
        super().__init__(zebra_stripes=True, cursor_type="row", **kwargs)
        self._columns_spec = columns
        self._columns_added = False

    def _ensure_columns(self) -> None:
        if not self._columns_added:
            for label, width in self._columns_spec:
                self.add_column(label, width=width, key=label)
            self._columns_added = True

    def _selected_key(self) -> str | None:
        try:
            if self.row_count == 0:
                return None
            row_key = self.coordinate_to_cell_key(self.cursor_coordinate).row_key
            return str(row_key.value) if row_key is not None else None
        except Exception:
            return None

    def update_rows(self, rows: list[dict], *, key_field: str) -> None:
        """rows: liste af dicts. Hver skal have key_field + én værdi pr. kolonne-label
        (nøgle = kolonne-label). Bevarer markør på valgt key."""
        self._ensure_columns()
        selected = self._selected_key()
        old_index = self.cursor_coordinate.row if self.row_count else 0
        new_keys = [str(r[key_field]) for r in rows]

        self.clear()  # ryd kun RÆKKER (ikke kolonner)
        for r in rows:
            cells = [r.get(label, "") for (label, _w) in self._columns_spec]
            self.add_row(*cells, key=str(r[key_field]))

        if self.row_count:
            target = restore_cursor_index(selected, new_keys, old_index)
            self.move_cursor(row=target)
