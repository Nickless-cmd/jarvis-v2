from __future__ import annotations

from core.memory.private_growth_note import build_private_growth_note_payload
from core.memory.private_inner_note import build_private_inner_note_payload
from core.memory.private_development_state import build_private_development_state_payload
from core.memory.private_reflective_selection import (
    build_private_reflective_selection_payload,
)
from core.memory.private_state import build_private_state_payload
from core.memory.private_temporal_promotion_signal import (
    build_private_temporal_promotion_signal_payload,
)
from core.memory.protected_inner_voice import build_protected_inner_voice_payload
from core.memory.private_self_model import build_private_self_model_payload
from core.runtime.db import (
    record_private_state,
    record_private_development_state,
    record_private_growth_note,
    record_private_inner_note,
    record_private_reflective_selection,
    record_private_self_model,
    record_private_temporal_promotion_signal,
    record_protected_inner_voice,
)


def write_private_terminal_layers(
    *,
    run_id: str,
    work_id: str,
    status: str,
    started_at: str | None,
    finished_at: str,
    user_message_preview: str | None,
    work_preview: str | None,
    capability_id: str | None,
) -> None:
    private_inner_note = build_private_inner_note_payload(
        run_id=run_id,
        work_id=work_id,
        status=status,
        user_message_preview=user_message_preview,
        work_preview=work_preview,
        capability_id=capability_id,
        created_at=started_at or finished_at,
    )
    private_growth_note = build_private_growth_note_payload(
        run_id=run_id,
        work_id=work_id,
        status=status,
        work_preview=work_preview,
        private_inner_note=private_inner_note,
        created_at=started_at or finished_at,
    )
    private_self_model = build_private_self_model_payload(
        run_id=run_id,
        private_inner_note=private_inner_note,
        private_growth_note=private_growth_note,
        created_at=started_at or finished_at,
        updated_at=finished_at,
    )
    private_reflective_selection = build_private_reflective_selection_payload(
        run_id=run_id,
        work_id=work_id,
        private_growth_note=private_growth_note,
        private_self_model=private_self_model,
        created_at=finished_at,
    )
    private_development_state = build_private_development_state_payload(
        private_growth_note=private_growth_note,
        private_self_model=private_self_model,
        private_reflective_selection=private_reflective_selection,
        created_at=started_at or finished_at,
        updated_at=finished_at,
    )
    private_state = build_private_state_payload(
        private_inner_note=private_inner_note,
        private_growth_note=private_growth_note,
        private_self_model=private_self_model,
        private_reflective_selection=private_reflective_selection,
        private_development_state=private_development_state,
        created_at=started_at or finished_at,
        updated_at=finished_at,
    )
    protected_inner_voice = build_protected_inner_voice_payload(
        run_id=run_id,
        work_id=work_id,
        private_state=private_state,
        private_self_model=private_self_model,
        private_development_state=private_development_state,
        private_reflective_selection=private_reflective_selection,
        created_at=finished_at,
    )
    private_temporal_promotion_signal = build_private_temporal_promotion_signal_payload(
        run_id=run_id,
        work_id=work_id,
        private_state=private_state,
        private_reflective_selection=private_reflective_selection,
        private_development_state=private_development_state,
        protected_inner_voice=protected_inner_voice,
        created_at=finished_at,
    )

    record_private_inner_note(**private_inner_note)
    record_private_growth_note(**private_growth_note)
    record_private_self_model(**private_self_model)
    record_private_reflective_selection(**private_reflective_selection)
    record_private_development_state(**private_development_state)
    record_private_state(**private_state)
    record_protected_inner_voice(**protected_inner_voice)
    record_private_temporal_promotion_signal(**private_temporal_promotion_signal)
