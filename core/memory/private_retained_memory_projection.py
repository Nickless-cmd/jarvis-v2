from __future__ import annotations


def build_private_retained_memory_projection(
    *,
    current_record: dict[str, object] | None,
    recent_records: list[dict[str, object]],
) -> dict[str, object]:
    if not current_record:
        return {
            "active": False,
            "current": None,
            "projection_id": None,
            "source": "private-retained-memory-record",
            "retained_focus": None,
            "retained_kind": None,
            "retention_scope": None,
            "confidence": None,
            "recent_record_ids": [],
            "created_at": None,
        }

    return {
        "active": True,
        "current": current_record,
        "projection_id": f"private-retained-memory-projection:{current_record['record_id']}",
        "source": "private-retained-memory-record",
        "retained_focus": current_record.get("retained_value"),
        "retained_kind": current_record.get("retained_kind"),
        "retention_scope": current_record.get("retention_scope"),
        "confidence": current_record.get("confidence"),
        "recent_record_ids": [
            str(record.get("record_id"))
            for record in recent_records
            if record.get("record_id")
        ][:5],
        "created_at": current_record.get("created_at"),
    }
