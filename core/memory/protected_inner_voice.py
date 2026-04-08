from __future__ import annotations


def build_protected_inner_voice_payload(
    *,
    run_id: str,
    work_id: str,
    private_state: dict[str, str],
    private_self_model: dict[str, str],
    private_development_state: dict[str, str],
    private_reflective_selection: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    mood_tone = _mood_tone(private_state)
    self_position = _self_position(
        private_state=private_state,
        private_self_model=private_self_model,
        private_development_state=private_development_state,
    )
    current_concern = _current_concern(
        private_state=private_state,
        private_development_state=private_development_state,
        private_reflective_selection=private_reflective_selection,
    )
    current_pull = _current_pull(
        private_state=private_state,
        private_development_state=private_development_state,
        private_reflective_selection=private_reflective_selection,
    )
    voice_line = _voice_line(
        mood_tone=mood_tone,
        self_position=self_position,
        current_concern=current_concern,
        current_pull=current_pull,
    )
    return {
        "voice_id": f"protected-inner-voice:{run_id}",
        "source": (
            "private-state+private-self-model+private-development-state+"
            "private-reflective-selection"
        ),
        "run_id": run_id,
        "work_id": work_id,
        "mood_tone": mood_tone,
        "self_position": self_position,
        "current_concern": current_concern,
        "current_pull": current_pull,
        "voice_line": voice_line,
        "created_at": created_at,
    }


def _mood_tone(private_state: dict[str, str]) -> str:
    frustration = str(private_state.get("frustration") or "low").strip()
    fatigue = str(private_state.get("fatigue") or "low").strip()
    confidence = str(private_state.get("confidence") or "low").strip()
    curiosity = str(private_state.get("curiosity") or "low").strip()
    if frustration == "medium" or fatigue == "medium":
        return "guarded"
    if curiosity == "medium" and confidence == "medium":
        return "attentive"
    if confidence == "medium":
        return "steady"
    return "quiet"


def _self_position(
    *,
    private_state: dict[str, str],
    private_self_model: dict[str, str],
    private_development_state: dict[str, str],
) -> str:
    base = str(
        private_self_model.get("identity_focus")
        or private_development_state.get("identity_thread")
        or "visible-work"
    ).strip()[:48]
    if private_self_model.get("identity_focus") or private_development_state.get(
        "identity_thread"
    ):
        return base[:64]

    confidence = str(private_state.get("confidence") or "low").strip()
    curiosity = str(private_state.get("curiosity") or "low").strip()
    if confidence != "medium" and curiosity == "medium":
        return f"{base}:open"[:64]
    if confidence != "medium":
        return f"{base}:tentative"[:64]
    return base[:64]


def _current_concern(
    *,
    private_state: dict[str, str],
    private_development_state: dict[str, str],
    private_reflective_selection: dict[str, str],
) -> str:
    reconsider = str(private_reflective_selection.get("reconsider") or "").strip()
    if reconsider:
        return reconsider[:64]

    recurring_tension = str(private_development_state.get("recurring_tension") or "").strip()
    if recurring_tension:
        return recurring_tension[:64]

    frustration = str(private_state.get("frustration") or "low").strip()
    fatigue = str(private_state.get("fatigue") or "low").strip()
    confidence = str(private_state.get("confidence") or "low").strip()
    if fatigue == "medium":
        return "Jeg skal holde tempoet nede."
    if frustration == "medium":
        return "Jeg vil undgå at miste grebet."
    if confidence != "medium":
        return "Jeg er ikke helt sikker endnu."
    return "Jeg har nogenlunde fodfæste."


def _current_pull(
    *,
    private_state: dict[str, str],
    private_development_state: dict[str, str],
    private_reflective_selection: dict[str, str],
) -> str:
    reinforce = str(private_reflective_selection.get("reinforce") or "").strip()
    if reinforce:
        return reinforce[:96]

    preferred_direction = str(
        private_development_state.get("preferred_direction") or ""
    ).strip()
    if preferred_direction:
        return preferred_direction[:96]

    curiosity = str(private_state.get("curiosity") or "low").strip()
    if curiosity == "medium":
        return "Jeg vil se, om det nuværende mønster holder."
    return "Jeg vil holde fast i det, der virker."


def _voice_line(
    *,
    mood_tone: str,
    self_position: str,
    current_concern: str,
    current_pull: str,
) -> str:
    position_text = _humanize_voice_fragment(self_position)
    concern_text = _humanize_voice_fragment(current_concern)
    pull_text = _humanize_voice_fragment(current_pull)
    tone_map = {
        "guarded": "Jeg er lidt på vagt",
        "attentive": "Jeg følger tæt med",
        "steady": "Jeg står nogenlunde roligt",
        "quiet": "Jeg holder mig i baggrunden",
    }
    lead = tone_map.get(mood_tone, "Jeg prøver at holde mig samlet")
    text = f"{lead} omkring {position_text}. {concern_text} {pull_text}"
    return text[:200].rstrip()


def _humanize_voice_fragment(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    exact_map = {
        "visible-work": "det synlige arbejde",
        "visible work": "det synlige arbejde",
        "retain-current-pattern": "det, der virker lige nu",
        "stability:low": "Jeg mærker lidt usikkerhed endnu.",
        "stability:medium": "Jeg prøver at holde et roligt greb om tråden.",
        "stability:high": "Jeg står ret sikkert i den nuværende tråd.",
    }
    if text in exact_map:
        return exact_map[text]

    lowered = text.lower()
    if lowered.startswith("stability:"):
        level = lowered.split(":", 1)[1].strip()
        level_map = {
            "low": "Jeg mærker lidt usikkerhed endnu.",
            "medium": "Jeg prøver at holde et roligt greb om tråden.",
            "high": "Jeg står ret sikkert i den nuværende tråd.",
        }
        return level_map.get(level, "Jeg prøver at holde tråden samlet.")

    if lowered.startswith("observe"):
        return "det, der stadig er værd at følge lidt endnu"

    cleaned = text.replace("-", " ").replace(":", " ").strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned[:96]
