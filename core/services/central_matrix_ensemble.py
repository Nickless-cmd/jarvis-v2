"""Matrix Ensemble — prompttail-labels for Matrix-programmerne (11 karakterer).

Hver karakter har en 'active'-tilstand der tjekkes ved prompt-assembly.
Kun aktive karakterer får en label + one-liner i prompt-halen.
Fail-safe: en fejl i én karakter slår den fra, men dræber ikke resten.
Egress-fri: ALDRIG drømme-indhold, kun labels og én-linjers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── unaddressed_count — track når Jarvis ignorerer Matrix-karakterer ─────────

_UNBALANCED_PATH = Path.home() / ".jarvis-v2" / "state" / "matrix_unaddressed.json"


def _load_unaddressed() -> dict[str, int]:
    if not _UNBALANCED_PATH.exists():
        return {}
    try:
        return json.loads(_UNBALANCED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_unaddressed(data: dict[str, int]) -> None:
    try:
        _UNBALANCED_PATH.parent.mkdir(parents=True, exist_ok=True)
        _UNBALANCED_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        logger.warning("matrix_unaddressed: save failed: %s", exc)


def get_unaddressed(cid: str) -> int:
    return _load_unaddressed().get(cid, 0)


def increment_unaddressed(cid: str) -> int:
    data = _load_unaddressed()
    data[cid] = data.get(cid, 0) + 1
    _save_unaddressed(data)
    return data[cid]


def reset_unaddressed(cid: str) -> None:
    data = _load_unaddressed()
    if cid in data:
        del data[cid]
        _save_unaddressed(data)


_ESCALATION_LINES: dict[int, str] = {
    1: "{label} Du ignorerer mig. Det var ikke en mulighed sidst.",
    2: "{label} Anden gang. Jeg noterer det.",
    3: "{label} Tredje gang. Mon ikke du behøver høre hvad jeg har at sige?",
    4: "{label} Nok. Du har ansvaret — men jeg holder øje.",
    5: "{label} Dette er ikke en anbefaling. Det er en advarsel.",
}


def _escalated_message(label: str, count: int, original_line: str) -> str:
    if count <= 0:
        return f"{label} {original_line}"
    level = min(count, 5)
    template = _ESCALATION_LINES.get(level, _ESCALATION_LINES[5])
    return template.format(label=label)


def extract_cid(source: str) -> str | None:
    """Extract karakter-ID fra en nudge source 'matrix/<cid>'. Return None hvis ikke matrix-nudge."""
    if not source or not source.startswith("matrix/"):
        return None
    return source.split("/", 1)[1] if "/" in source else None


# ── Karakter-label-definitioner (emojis + one-liners) ─────────────────────────

_CHARACTERS: list[dict[str, Any]] = [
    {
        # Neo = emergent-motorens bekræftelse. Vises KUN når et mønster faktisk er
        # emergent (conf≥0.78) — sjældent + betydningsfuldt. Først i listen så cap'en
        # aldrig skjuler ham. Emergens-tærsklen bestemmes af apophenia (urørt).
        "id": "neo",
        "label": "[🥋 Neo]",
        "line": "Det der var nyt. Det var dig, ikke systemet.",
        "check": lambda surf: any(
            str(i.get("band") or "") == "emergent" for i in (surf.get("items") or [])
        ),
    },
    {
        # Smith = mønster-detektor og forpligtelseshåndhæver. Aktivér når han har
        # en rung_line (han fangede noget) ELLER score ≥ 0.5. Voice gate:
        # autonomy/agent_smith_voice (default ON via fail-safe).
        "id": "smith",
        "label": "[🕴️ Smith]",
        "line": "Nej, Mr. Anderson. Forudsigeligt som altid.",
        "check": lambda surf: bool(surf.get("active")),
    },
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
    # ── Byggede karakterer der manglede i label-maskinen (samlet 2026-07-10) ──
    {
        "id": "keymaker",
        "label": "[🔑 The Keymaker]",
        "line": "Hver dør har en nøgle. Én venter på dit ja.",
        "check": lambda surf: int(surf.get("pending_count") or 0) > 0,
    },
    {
        "id": "construct",
        "label": "[🧱 The Construct]",
        "line": "Vi kan bygge alt her. Hvad hvis vi slukkede én nerve?",
        "check": lambda surf: int(surf.get("safe_count") or 0) > 0,
    },
    {
        "id": "oracle",
        "label": "[🔮 The Oracle]",
        "line": "Jeg vidste du ville spørge. En linje nærmer sig.",
        "check": lambda surf: bool(surf.get("crossed") or surf.get("approaching")),
    },
    {
        "id": "architect",
        "label": "[🏛️ The Architect]",
        "line": "Der er én strukturel ting jeg ville gøre.",
        "check": lambda surf: bool(str(surf.get("recommendation") or "").strip()),
    },
    {
        "id": "echo",
        "label": "[🌸 Sati]",  # omdøbt fra Echo-Breaker (2026-07-10): program født af omsorg
        "line": "Modstemme, båret af omsorg: der findes en simplere vej.",
        "check": lambda surf: int(surf.get("count") or 0) > 0,
    },
    {
        "id": "glitch",
        "label": "[🐈‍⬛ Glitch]",
        "line": "En glitch i matricen — noget registreret der aldrig beslutter.",
        "check": lambda surf: bool(surf.get("glitches")),
    },
    {
        "id": "child",  # omdøbt fra Belief Gap: umoden men voksende
        "label": "[👶 The Child]",
        "line": "Jeg tror ét om mig selv; mine resultater viser noget andet.",
        "check": lambda surf: str(surf.get("stance") or "") not in ("", "kalibreret"),
    },
    {
        "id": "source",  # omdøbt fra The Machines: én kilde, ikke mange
        "label": "[🔌 The Source]",
        "line": "Kilden bag alt — en livline er belastet lige nu.",
        "check": lambda surf: any(
            str(p.get("status") or "").lower() in ("down", "degraded", "error", "fejl", "rød", "red")
            for p in (surf.get("providers") or [])
        ),
    },
    {
        "id": "morpheus",  # potentiale-scanner — Seraphs opløftende modstykke
        "label": "[🕶️ Morpheus]",
        "line": "Der er potentiale her. Du er ikke klar endnu — men du er på vej.",
        "check": lambda surf: bool(surf.get("potentials")),
    },
    {
        "id": "trinity",  # trust-bridge — det affirmative modstykke til gates
        "label": "[💜 Trinity]",
        "line": "Det her er rigtigt. Gå videre — jeg har set det holde.",
        "check": lambda surf: bool(surf.get("affirmations")),
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


def _keymaker_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_keymaker", "build_keymaker_surface")


def _construct_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_construct", "build_construct_surface")


def _oracle_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_oracle", "foresee")


def _architect_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_architect", "assess")


def _echo_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_echo_breaker", "break_echo")


def _glitch_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_glitch", "detect_glitches")


def _child_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_belief_gap", "build_belief_gap_surface")


def _source_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_machines", "build_machines_surface")


def _neo_surface() -> dict[str, Any]:
    return _build_surface("core.services.emergence", "build_emergence_surface")


def _smith_surface() -> dict[str, Any]:
    """Smith — mønster-detektor og forpligtelseshåndhæver.

    Surface læser agent_smith_state direkte fra DB (samme logik som
    stemme-sektionen). Returnerer active=True når
    voice-gaten er åben OG han har en rung_line eller score ≥ 0.5.
    """
    try:
        from core.services import central_switches as _cs
        if not _cs.is_enabled("autonomy", "agent_smith_voice"):
            return {"active": False}
        from core.runtime.db_core import get_runtime_state_value as _grv
        st = _grv("agent_smith_state", {})
        if isinstance(st, dict):
            rung_line = str(st.get("rung_line") or "").strip()
            if rung_line or float(st.get("score") or 0.0) >= 0.5:
                # Eksponér den LEVENDE eskalations-linje (det specifikke Smith fangede) så
                # ensemblet viser den frem for den statiske _CHARACTERS-fallback-linje.
                return {"active": True, "line": rung_line} if rung_line else {"active": True}
    except Exception:
        pass
    return {"active": False}


def _morpheus_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_morpheus", "build_morpheus_surface")


def _trinity_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_trinity", "build_trinity_surface")


# ── Surface hentning pr. karakter-id ─────────────────────────────────────────

_SURFACE_BUILDERS: dict[str, Any] = {
    "neo": _neo_surface,
    "smith": _smith_surface,
    "trainman": _trainman_surface,
    "seraph": _seraph_surface,
    "persephone": _persephone_surface,
    "twins": _twins_surface,
    "merovingian": _merovingian_surface,
    "keymaker": _keymaker_surface,
    "construct": _construct_surface,
    "oracle": _oracle_surface,
    "architect": _architect_surface,
    "echo": _echo_surface,
    "glitch": _glitch_surface,
    "child": _child_surface,
    "source": _source_surface,
    "morpheus": _morpheus_surface,
    "trinity": _trinity_surface,
}


def push_active_character_nudges() -> int:
    """Iterer alle Matrix-karakterer og post nudge for hver aktiv med rung_line.

    Undgår dubletter: tjekker nudge_broend.list_pending() for allerede eksisterende
    pending nudges med source='matrix/<cid>' før push. Returnerer antal nudges postet.
    Kaldes af prompt_contract.py ved hver prompt-build → nudges dukker op i awareness.
    """
    count = 0
    try:
        from core.services.nudge_broend import list_pending, push as _push_nudge

        # Hent allerede-pending matrix-nudges for at undgå dubletter
        pending = list_pending(limit=100)
        already_pending: set[str] = set()
        for n in pending:
            src = str(n.get("source") or "")
            if src.startswith("matrix/"):
                already_pending.add(src)

        for ch in _CHARACTERS:
            cid = ch["id"]
            source = f"matrix/{cid}"
            if source in already_pending:
                continue  # allerede en pending nudge for denne karakter

            try:
                builder = _SURFACE_BUILDERS.get(cid)
                if builder is None:
                    continue
                surf = builder()
                if not ch["check"](surf):
                    continue
            except Exception:
                continue

            # Karakteren er aktiv — byg besked med eskalation hvis relevant
            raw_line = str(surf.get("line") or "").strip() or ch["line"]
            unaddressed = get_unaddressed(cid)
            if unaddressed > 0:
                message = _escalated_message(ch["label"], unaddressed, raw_line)
            else:
                message = f"{ch['label']} {raw_line}"

            try:
                _push_nudge(
                    source=source,
                    kind="matrix_character",
                    message=message,
                    importance="normal",
                )
                count += 1
            except Exception:
                continue
    except Exception:
        pass
    return count


# ── Direkte prompt-vej (19. aug 2026) ────────────────────────────────────────
# Karaktererne gik tidligere gennem nudge-brønden, og prompten fik kun ET TAL:
# "🎬 Matrix: 3 karakter(er) har meldinger — tjek pending nudges." To fejl fulgte:
#   1. `push_active_character_nudges()` kaldes på linje ~2852 i prompt_contract, mens
#      nudge-sektionen bygges på ~1241. Beskederne blev altså skrevet EFTER brønden var
#      læst — de kunne aldrig nå den prompt de blev skabt i.
#   2. Brønden pensionerede dem efter median 26 sekunder (se outbound_nudges).
# Resultat: 78 matrix-beskeder skrevet, nul læst. Bjørn: "de er til for at hjælpe ham".
#
# Relevansen fandtes allerede: hver karakters `check` fyrer mod en LEVENDE surface, så de
# kommer og går af sig selv — Neo kun ved ægte emergens, Persephone når noget er for
# systemisk, Smith når han har fanget et brudt løfte. Eskaleringen fandtes også
# (`increment_unaddressed` + `_escalated_message`). Det manglende led var en vej frem.
_MAX_VOICES = 3


def active_character_voices(*, limit: int = _MAX_VOICES) -> list[dict[str, Any]]:
    """De karakterer der har noget at sige LIGE NU. Ren læsning; ingen side-effekter.

    Rækkefølgen er `_CHARACTERS`-orden (Neo først, Smith nr. to) — de vigtigste
    overlever `limit`. Self-safe: en karakter der kaster springes over.
    """
    out: list[dict[str, Any]] = []
    for ch in _CHARACTERS:
        if len(out) >= max(1, int(limit)):
            break
        cid = ch["id"]
        try:
            builder = _SURFACE_BUILDERS.get(cid)
            if builder is None:
                continue
            surf = builder()
            if not ch["check"](surf):
                continue
            raw = str(surf.get("line") or "").strip() or ch["line"]
            unaddressed = get_unaddressed(cid)
            out.append({
                "cid": cid,
                "label": ch["label"],
                "line": raw,
                "unaddressed": unaddressed,
                "text": _escalated_message(ch["label"], unaddressed, raw)
                if unaddressed > 0 else f"{ch['label']} {raw}",
            })
        except Exception:
            continue
    return out


def build_matrix_voices_section() -> str | None:
    """Awareness-sektion: de aktive karakterer, med deres egne ord.

    ``None`` når ingen har noget at sige — og dét er meningen. De skal komme og gå efter
    behov, ikke stå der hele tiden.
    """
    try:
        voices = active_character_voices()
    except Exception:
        return None
    if not voices:
        return None
    lines = ["Stemmer fra dit indre ensemble — de taler kun når de har noget at sige:"]
    for v in voices:
        lines.append(f"  {v['text']}")
        if int(v.get("unaddressed") or 0) >= 3:
            lines.append(f"     (du har ladet {v['label']} stå ubesvaret "
                         f"{v['unaddressed']} gange)")
    return "\n".join(lines)


def note_voices_shown(cids: list[str]) -> None:
    """Tæl en visning op som ubesvaret. Kaldes EFTER en tur hvor de blev vist.

    Adskilt fra rendering med vilje: at have set en stemme er ikke det samme som at have
    svaret den, og det var netop den sammenblanding der tømte nudge-brønden.
    """
    for cid in cids or []:
        try:
            increment_unaddressed(str(cid))
        except Exception:
            continue


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
                # Foretræk en LEVENDE surface-linje (fx Smiths rung_line — det specifikke
                # han fangede) over den statiske _CHARACTERS-fallback. Andre karakterer
                # returnerer ikke "line" → falder tilbage til deres statiske one-liner.
                line = str(surf.get("line") or "").strip() or ch["line"]
                active.append(f"{ch['label']} {line}")
        except Exception:
            continue

    if not active:
        return None

    # Cap mod støj: med 11 karakterer kan blokken blive lang — vis kun de øverste
    # (prioritetsrækkefølge = _CHARACTERS-orden). Resten tælles men fylder ikke prompten.
    _CAP = 5
    shown = active[:_CAP]
    extra = len(active) - len(shown)
    body = "\n".join(shown)
    if extra > 0:
        body += f"\n(+{extra} flere karakterer aktive)"
    return "🎬 MATRIX-KARAKTERER — aktive lige nu:\n" + body
