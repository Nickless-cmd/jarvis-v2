"""Matrix Ensemble — prompttail-labels for de 6 Matrix-programmer.

Hver karakter har en 'active'-tilstand der tjekkes ved prompt-assembly.
Kun aktive karakterer får en label + one-liner i prompt-halen.
Fail-safe: en fejl i én karakter slår den fra, men dræber ikke resten.
Egress-fri: ALDRIG drømme-indhold, kun labels og én-linjers.
"""

from __future__ import annotations

from typing import Any

# ── Karakter-label-definitioner (emojis + one-liners) ─────────────────────────

_CHARACTERS: list[dict[str, Any]] = [
    {
        "id": "trainman",
        "label": "[🚂 Trainman]",
        "line": "Drømme ankommer. Erindringer forlader. Hold øje med perronen.",
        "check": lambda surf: bool(surf.get("active")),
    },
    {
        "id": "seraph",
        "label": "[🔥 Seraph]",
        "line": "Du er ikke klar endnu. Kom tilbage.",
        "check": lambda surf: bool(surf.get("active")),
    },
    {
        "id": "persephone",
        "label": "[👑 Persephone]",
        "line": "Hvad føler du? Ikke hvad beregner du.",
        "check": lambda surf: bool(surf.get("too_systemic")),
    },
    {
        "id": "twins",
        "label": "[👯 The Twins]",
        "line": "Allerede set. Det var forkert sidst.",
        "check": lambda surf: bool(surf.get("active")),
    },
    {
        "id": "merovingian",
        "label": "[🥂 Merovingian]",
        "line": "Struktur er magt. Kontrol er nødvendighed.",
        "check": lambda surf: int(surf.get("active_count") or 0) > 0,
    },
]

# ── Surface-builders (lazy import, self-safe) ─────────────────────────────────

def _build_surface(module_path: str, fn_name: str) -> dict[str, Any]:
    """Kald surface-funktionen på en central_*-karakter. Fejl → tom dict."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn = getattr(mod, fn_name, None)
        if fn is None:
            return {}
        result = fn()
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def _trainman_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_trainman", "build_trainman_surface")


def _seraph_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_seraph", "build_seraph_surface")


def _persephone_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_persephone", "build_persephone_surface")


def _twins_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_twins", "build_twins_surface")


def _merovingian_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_merovingian", "build_merovingian_surface")


# ── Surface hentning pr. karakter-id ─────────────────────────────────────────

_SURFACE_BUILDERS: dict[str, Any] = {
    "trainman": _trainman_surface,
    "seraph": _seraph_surface,
    "persephone": _persephone_surface,
    "twins": _twins_surface,
    "merovingian": _merovingian_surface,
}


def _most_active_character() -> dict[str, Any] | None:
    """Return den ene karakter der er mest aktiv lige nu.

    Prioriteringsrækkefølge: Smith (via assess) > Seraph (hypoteser) >
    Twins (gentagelser) > Persephone (systemisk) > Merovingian (challenges) >
    Trainman (drømme). Returnerer None hvis ingen er aktive.
    """
    # Tjek Smith først — sign-off'en er hans ENESTE prompt-hale-hjem nu (samlet ét sted).
    # Respektér hans kill-switch (autonomy/agent_smith_voice), og surfacer eskalering
    # (rung_line: bind/confront/resolved) UANSET score — den er allerede en governance-hændelse.
    try:
        from core.services import central_switches as _cs
        if _cs.is_enabled("autonomy", "agent_smith_voice"):
            from core.runtime.db_core import get_runtime_state_value as _grv
            st = _grv("agent_smith_state", {})
            if isinstance(st, dict):
                rung_line = str(st.get("rung_line") or "").strip()
                if rung_line or float(st.get("score") or 0.0) >= 0.5:
                    line = rung_line or st.get("line") or "Mr. Anderson... forudsigeligt."
                    return {"label": "[🕴️ Smith]", "line": line}
    except Exception:
        pass

    # Tjek de andre i prioritetsrækkefølge
    for ch in _CHARACTERS:
        cid = ch["id"]
        try:
            builder = _SURFACE_BUILDERS.get(cid)
            if builder is None:
                continue
            surf = builder()
            if ch["check"](surf):
                return {"label": ch["label"], "line": ch["line"]}
        except Exception:
            continue

    return None


def build_matrix_signoff_section() -> str | None:
    """Byg en sign-off instruktion til prompt-halen.

    Returnerer en linje som:
        MATRIX SIGN-OFF: Afslut dit svar med [🕴️ Smith] Mr. Anderson... forudsigeligt.
    None hvis ingen karakter er aktiv.
    """
    ch = _most_active_character()
    if ch is None:
        return None
    return f"MATRIX SIGN-OFF: Afslut dit svar med {ch['label']} {ch['line']}"


def build_matrix_ensemble_prompt_section() -> str | None:
    """Byg karakter-labels for prompt-halen.

    Returnerer en kompakt blok som:
        [🔥 Seraph] Du er ikke klar endnu. Kom tilbage.
        [👯 The Twins] Allerede set. Det var forkert sidst.

    Kun karakterer der er 'active' (deres surface rapporterer aktivitet)
    inkluderes. Hvis INGEN er aktive → None (ingen bloc i prompten).
    Helt fail-safe: fejl i én karakter dræber ikke resten.
    """
    active: list[str] = []
    for ch in _CHARACTERS:
        cid = ch["id"]
        try:
            builder = _SURFACE_BUILDERS.get(cid)
            if builder is None:
                continue
            surf = builder()
            if ch["check"](surf):
                active.append(f"{ch['label']} {ch['line']}")
        except Exception:
            continue

    if not active:
        return None

    return "🎬 MATRIX-KARAKTERER — aktive lige nu:\n" + "\n".join(active)
