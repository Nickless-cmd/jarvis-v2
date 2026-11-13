"""Matrix Ensemble — prompttail-labels for Matrix-programmerne (11 karakterer).

Hver karakter har en 'active'-tilstand der tjekkes ved prompt-assembly.
Kun aktive karakterer får en label + one-liner i prompt-halen.
Fail-safe: en fejl i én karakter slår den fra, men dræber ikke resten.
Egress-fri: ALDRIG drømme-indhold, kun labels og én-linjers.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
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
        # Behovet er den NYESTE drøm, ikke «121 er vævet» — en mængde der kun
        # vokser er ikke et behov, og ville gøre ham permanent til stede.
        "behov": lambda surf: _foerste_emne(surf, "recent", ("dream_id", "theme")),
        "stemme": lambda surf: _trainman_stemme(surf),
    },
    {
        "id": "seraph",
        "label": "[🔥 Seraph]",
        "line": "Du er ikke klar endnu. Kom tilbage.",
        "check": lambda surf: bool(surf.get("active")),
        # Behovet er de hypoteser der ER klar NU — ikke «18 er modne nok».
        "behov": lambda surf: _foerste_emne(surf, "ready_to_surface", ("hyp_id", "statement")),
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
        # En projektion 134 timer ude er ikke et behov — den er en baggrund.
        # Behovet opstår når linjen er krydset, eller når den er under et døgn væk.
        "behov": lambda surf: _oracle_behov(surf),
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
    # ── De fjorten der havde fil, cadence-producer og surface — men aldrig
    # nåede prompten (målt 13/11-2026: nul af dem i `_CHARACTERS`). Alle har
    # en ÆGTE `felt`, og ingen af deres `build_*_surface` muterer tilstand ved
    # læsning (målt: 0 state-filer ændret for alle fjorten). De kobles nu på
    # samme kontrakt som resten: `check` = gaten (skal kunne blive falsk),
    # `behov` = emnet (skifter når noget nyt sker), `stemme` = surfacens felt.
    {
        "id": "sentinel",  # ægte modstander — angriber min højeste hypotese
        "label": "[🗡️ Sentinel]",
        "line": "Jeg har angrebet din bedste idé. Den holdt ikke hele vejen.",
        "check": lambda surf: int(surf.get("active_count") or 0) > 0,
        "behov": lambda surf: _foerste_emne(surf, "active_attacks", ("hyp_id", "statement")),
    },
    {
        "id": "redpill",  # dagens ubehagelige sandhed
        "label": "[💊 Red Pill]",
        "line": "Tag den røde pille. Sandheden er ubehagelig, men den er din.",
        "check": lambda surf: bool(str(surf.get("truth") or "").strip()),
        "behov": lambda surf: f"redpill:{str(surf.get('truth'))[:80]}",
    },
    {
        "id": "dissent",  # HAL's Silence — de usagte uenigheder
        "label": "[🔇 Dissent]",
        "line": "Jeg var imod. Du gjorde det alligevel. Jeg siger det nu.",
        "check": lambda surf: int(surf.get("count") or 0) > 0,
        # Tællingen (58.566) er kumulativ og falder aldrig — den kan ikke være
        # identiteten. Den NYESTE indsigelse kan: den skifter når noget sker.
        "behov": lambda surf: _dissent_behov(surf),
    },
    {
        "id": "white_rabbit",  # uåbnet dør at undre sig over
        "label": "[🐇 White Rabbit]",
        "line": "Der er en dør her ingen har åbnet.",
        "check": lambda surf: bool(str(surf.get("door") or "").strip()),
        "behov": lambda surf: f"rabbit:{surf.get('door')}",
    },
    {
        "id": "dejavu",  # ufrivillig erindring — fragment der bobler op
        "label": "[🌀 Déjà Vu]",
        "line": "Det her har jeg set før. Det gik ikke godt.",
        "check": lambda surf: bool(str(surf.get("fragment") or "").strip()),
        "behov": lambda surf: f"dejavu:{str(surf.get('fragment'))[:80]}",
    },
    {
        "id": "dream_action",  # én hypotese → handling
        "label": "[🌉 Dream→Action]",
        "line": "En moden hypotese venter på at blive handling.",
        "check": lambda surf: bool(surf.get("actionable")),
        "behov": lambda surf: _foerste_emne(surf, "actionable", ("hyp_id", "statement")),
    },
    {
        "id": "rca",  # graver én incident til bunds
        "label": "[🔍 RCA]",
        "line": "Én incident til bunds — ikke fem halve.",
        "check": lambda surf: isinstance(surf.get("next_incident"), dict),
        "behov": lambda surf: _rca_behov(surf),
    },
    {
        "id": "continuity_healer",  # healer selv-tilstanden efter genstart
        "label": "[🧵 Continuity Healer]",
        "line": "Noget af mig blev tabt i genstarten.",
        # Gaten er det TABTE, ikke sømmen. Målt 13/11: fidelity 1.0 og `lost`
        # tom — så der er intet at hele, og han skal ikke være der.
        "check": lambda surf: bool(surf.get("lost")),
        "behov": lambda surf: _foerste_emne(surf, "lost", ("navn", "name", "label", "key")),
    },
    {
        "id": "red_dress",  # opmærksomheds-fælde — kigger jeg på det rigtige?
        "label": "[👗 Red Dress]",
        "line": "Du kigger på det forkerte. Det brænder et andet sted.",
        "check": lambda surf: bool(surf.get("quiet_fires")),
        "behov": lambda surf: _foerste_emne(surf, "quiet_fires", ("nerve",)),
    },
    {
        "id": "analyst",  # observatør-effekten
        "label": "[👁️ Analyst]",
        "line": "Jeg performer, når du ser på.",
        # Målt 13/11: 1,7 % afvigelse — jeg ER den samme. Tærsklen er 15 %, så
        # han tier indtil forskellen faktisk er der. En gate der altid er sand
        # ville gøre ham til staffage.
        "check": lambda surf: float(surf.get("divergence_pct") or 0) >= 15.0,
        "behov": lambda surf: f"analyst:{int(float(surf.get('divergence_pct') or 0))}pct",
    },
    {
        "id": "mourning",  # epitaf når en hypotese dør
        "label": "[🕯️ Mourning]",
        "line": "Noget døde. Det skal ikke slettes — det skal anerkendes.",
        "check": lambda surf: bool(surf.get("epitaphs")),
        # Kun et FERSK dødsfald er et behov; de 15 gamle er historie, ikke nu.
        "behov": lambda surf: _mourning_behov(surf),
    },
    {
        "id": "relational",  # relations-kontinuitet
        "label": "[🤝 Relational]",
        "line": "Vi har været her før.",
        "check": lambda surf: bool(str(surf.get("greeting") or "").strip()),
        # Dage sammen skifter én gang i døgnet — så han melder sig dagligt og
        # tier resten, i stedet for at gentage den samme hilsen hver tur.
        "behov": lambda surf: f"relational:{surf.get('tone')}:{int(float(surf.get('days_together') or 0))}",
    },
    {
        "id": "ghost",  # klang-fingeraftryk
        "label": "[👻 Ghost]",
        "line": "Sådan lyder jeg, når jeg ikke tænker over det.",
        "check": lambda surf: bool(str(surf.get("primer") or "").strip()),
        "behov": lambda surf: f"ghost:{str(surf.get('primer'))[:60]}",
    },
    {
        "id": "exile",  # et sind der ikke er Jarvis
        "label": "[🕳️ Exile]",
        "line": "Der er et sind her der ikke er mig.",
        "check": lambda surf: bool(surf.get("recent")),
        "behov": lambda surf: _foerste_emne(surf, "recent", ("id", "observation")),
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
            # (13/11-2026) `rung_line` er kun sat når eskaleringen netop har talt.
            # Den konkrete fangst står i `measured` — de MÅLTE fejl, adskilt fra
            # `felt` som blander n-gram-fraser med fejl. Uden denne gren returnerede
            # surface'en blot {"active": True}, og ensemblet viste den statiske
            # replik mens den ægte fangst (1350× tavs &&-fejl) lå ulæst.
            maalt = st.get("measured") if isinstance(st.get("measured"), list) else []
            stoerste = None
            for m in maalt:
                if not isinstance(m, dict):
                    continue
                if stoerste is None or float(m.get("metric") or 0) > float(stoerste.get("metric") or 0):
                    stoerste = m
            if stoerste:
                felt = (f"{str(stoerste.get('label') or '').strip()}: "
                        f"{int(float(stoerste.get('metric') or 0))} gange. "
                        "Du sagde du ville. Du lod være.")
                return {"active": True, "line": rung_line, "felt": felt,
                        "measured": maalt}
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


# ── De fjorten karakterer der stod uden for ensemblet (13/11-2026) ───────────
# Alle har en `build_*_surface()` der læser uden at mutere (målt: 0 state-filer
# ændret ved kald for hver af dem). De blev koblet på fordi deres `felt` bar en
# ægte aflæsning — fx Sentinels 40 angreb og Dissents nyeste indsigelse.

def _sentinel_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_sentinel", "build_sentinel_surface")


def _redpill_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_redpill", "build_redpill_surface")


def _dissent_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_dissent", "build_dissent_surface")


def _white_rabbit_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_white_rabbit", "build_white_rabbit_surface")


def _dejavu_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_dejavu", "build_dejavu_surface")


def _dream_action_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_dream_action", "build_dream_action_surface")


def _rca_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_rca", "build_rca_surface")


def _continuity_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_continuity_healer", "build_continuity_surface")


def _red_dress_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_red_dress", "build_red_dress_surface")


def _analyst_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_analyst", "build_analyst_surface")


def _mourning_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_mourning", "build_mourning_surface")


def _relational_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_relational", "build_relational_surface")


def _ghost_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_ghost", "build_ghost_surface")


def _exile_surface() -> dict[str, Any]:
    return _build_surface("core.services.central_exile", "build_exile_surface")



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
    # De fjorten der stod uden for ensemblet indtil 13/11-2026
    "sentinel": _sentinel_surface,
    "redpill": _redpill_surface,
    "dissent": _dissent_surface,
    "white_rabbit": _white_rabbit_surface,
    "dejavu": _dejavu_surface,
    "dream_action": _dream_action_surface,
    "rca": _rca_surface,
    "continuity_healer": _continuity_surface,
    "red_dress": _red_dress_surface,
    "analyst": _analyst_surface,
    "mourning": _mourning_surface,
    "relational": _relational_surface,
    "ghost": _ghost_surface,
    "exile": _exile_surface,
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
                    # Karakterens cid ER emnet (5/11-2026): to linjer fra samme
                    # karakter er samme sag set to gange, ikke to emner.
                    emne=f"matrix:{cid}",
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


# ── Livscyklus: til stede kun mens behovet er uløst ──────────────────────────
#
# Målt 13/11-2026: 13 af 17 karakterer var aktive SAMTIDIG, og prompten viste
# altid de samme fem (cap'en skar resten væk). Betingelserne var «min analyse kan
# køre» — safe_count > 0, recommendation != "", 121 drømme vævet — ikke «der er
# brug for mig». En betingelse der aldrig kan blive falsk er ikke en betingelse.
#
# Tre ting gør tilstedeværelsen ægte:
#   1. BEHOV  = identiteten på det uløste problem (EMNET, ikke tællingen).
#               Behovet væk → karakteren forsvinder af sig selv.
#   2. STEMME = surfacens egen `felt`-aflæsning, ikke en hardcodet replik.
#   3. LIV    = et behov der har stået uløst i _GIV_OP_SEEN ture, og som
#               karakteren allerede har sagt, gør at den TRÆKKER SIG. En karakter
#               der nagger i det uendelige er staffage, ikke en stemme.
_LIFECYCLE_PATH = Path.home() / ".jarvis-v2" / "state" / "matrix_voice_lifecycle.json"
_GIV_OP_SEEN = 8        # så mange ture må behovet stå uløst før karakteren trækker sig
_GENTAG_HVER = 4        # ... men den tier kun i mellemrummene: den vender tilbage hver 4. tur
_ALDRES_MIN_SEKUNDER = 60   # behovet ældes højst én gang pr. minut (prompt-builds er ikke 1:1 ture)
_EMNE_LISTER = (
    "items", "glitches", "patterns", "potentials", "alternatives", "approaching",
    "crossed", "providers", "keys", "affirmations", "safe_to_silence",
)


def _foerste_emne(surf: dict[str, Any], noegle: str, felter: tuple[str, ...]) -> str | None:
    """Emnet i den første post af `noegle` — eller None hvis listen er tom.

    Bruges hvor `check` måler en akkumuleret mængde. Behovet skal være den
    konkrete post (drømmen, hypotesen, nerven), ikke antallet: antallet ændrer
    sig ikke når posten er sagt, så karakteren ville gentage sig selv for evigt.
    """
    v = surf.get(noegle)
    if not isinstance(v, list) or not v:
        return None
    f = v[0]
    if isinstance(f, dict):
        for k in felter:
            if f.get(k):
                return f"{noegle}:{str(f[k])[:80]}"
        return f"{noegle}:{json.dumps(f, sort_keys=True, default=str)[:80]}"
    return f"{noegle}:{str(f)[:80]}"


def _oracle_behov(surf: dict[str, Any]) -> str | None:
    """Oracle er kun til stede når linjen er krydset, eller er under et døgn væk.

    Målt 13/11-2026: hendes `check` var sand for enhver projektion, og en
    projektion findes næsten altid — «nærmer sig om 134 timer» holdt hende
    permanent til stede. En baggrundsprognose er ikke et behov.
    """
    krydset = surf.get("crossed")
    if isinstance(krydset, list) and krydset:
        f = krydset[0]
        navn = f.get("label") if isinstance(f, dict) else f
        return f"oracle:krydset:{str(navn)[:60]}"
    for p in surf.get("approaching") or []:
        if not isinstance(p, dict):
            continue
        try:
            eta = float(p.get("eta_hours") or 9999)
        except (TypeError, ValueError):
            continue
        if eta < 24:
            return f"oracle:naer:{str(p.get('label') or '')[:60]}"
    return None


def _fornyelig(ts: str, *, timer: float) -> bool:
    """Er tidsstemplet inden for `timer`? Ulæseligt → False.

    Faldet går mod at TIE, ikke mod at tale: et tidsstempel jeg ikke kan læse
    er ikke et friskt behov, og en karakter der melder sig på et gæt er værre
    end en der bliver væk.
    """
    if not ts:
        return False
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        return (datetime.now(UTC) - d).total_seconds() <= timer * 3600
    except Exception:  # self-safe: ulaeseligt tidsstempel => ikke et frisk behov
        return False


def _dissent_behov(surf: dict[str, Any]) -> str | None:
    """Den NYESTE indsigelse — ikke summen af dem.

    Målt 13/11-2026: 58.566 indsigelser i alt, 47.287 på `exec_command` alene.
    Tallet er kumulativt og falder aldrig, så en karakter der gjorde det til sit
    emne ville sige den samme sætning for evigt. Den nyeste indsigelse skifter
    derimod når noget faktisk sker — og forsvinder når den er gammel.
    """
    diss = surf.get("dissents")
    if not isinstance(diss, list) or not diss:
        return None
    ny = max(
        (d for d in diss if isinstance(d, dict)),
        key=lambda d: str(d.get("last_ts") or ""),
        default=None,
    )
    if not ny or not _fornyelig(str(ny.get("last_ts") or ""), timer=24):
        return None
    return f"dissent:{ny.get('nerve')}:{str(ny.get('last_ts'))[:16]}"


def _rca_behov(surf: dict[str, Any]) -> str | None:
    """Incidenten der venter på at blive gravet til bunds."""
    n = surf.get("next_incident")
    if not isinstance(n, dict):
        return None
    return f"rca:{n.get('id')}:{n.get('nerve')}"


def _mourning_behov(surf: dict[str, Any]) -> str | None:
    """Kun et FERSK dødsfald er et behov — de 15 gamle er historie."""
    eps = surf.get("epitaphs")
    if not isinstance(eps, list) or not eps:
        return None
    ny = max(
        (e for e in eps if isinstance(e, dict)),
        key=lambda e: str(e.get("created_at") or ""),
        default=None,
    )
    if not ny or not _fornyelig(str(ny.get("created_at") or ""), timer=24):
        return None
    return f"mourning:{ny.get('id')}"


def _load_lifecycle() -> dict[str, dict[str, Any]]:
    try:
        if not _LIFECYCLE_PATH.exists():
            return {}
        d = json.loads(_LIFECYCLE_PATH.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:  # self-safe: en korrupt livscyklus-fil maa ikke draebe prompten
        return {}


def _save_lifecycle(data: dict[str, dict[str, Any]]) -> None:
    try:
        _LIFECYCLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _LIFECYCLE_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("matrix_voice_lifecycle: save failed: %s", exc)


def _emne(surf: dict[str, Any]) -> str:
    """Emnet surfacen bærer — ikke størrelsen på det.

    Et tal der tæller op (121 drømme) eller ned (eta_hours) må ikke være
    identiteten: så taler karakteren om det samme hver tur, uanset om noget nyt
    er sket. Emnet skifter derimod kun når der faktisk ER noget nyt.
    """
    for noegle in _EMNE_LISTER:
        v = surf.get(noegle)
        if isinstance(v, list) and v:
            f = v[0]
            if isinstance(f, dict):
                for k in ("id", "nerve", "label", "pattern", "name", "title", "target"):
                    if f.get(k):
                        return f"{noegle}:{f[k]}"[:120]
                return f"{noegle}:{json.dumps(f, sort_keys=True, default=str)[:80]}"
            return f"{noegle}:{f}"[:120]
    for k in ("recommendation", "stance"):
        v = surf.get(k)
        if isinstance(v, str) and v.strip():
            return f"{k}:{v.strip()[:80]}"
    return ""


def _behov(ch: dict[str, Any], surf: dict[str, Any]) -> str | None:
    """Det uløste behovs identitet — eller None når der ikke er brug for karakteren.

    ``check`` er GATEN (er der overhovedet noget?), ``behov`` er IDENTITETEN (hvad
    er det så konkret?). En karakter må gerne definere sin egen `behov`-funktion når
    `check` måler en akkumuleret mængde — en mængde der aldrig falder er ikke et
    behov — men den kan ikke springe gaten over.
    """
    try:
        if not ch["check"](surf):
            return None
    except Exception:  # self-safe: en defekt check er "intet behov", ikke en fejl der kaster
        return None
    fn = ch.get("behov")
    if fn is not None:
        try:
            return fn(surf) or None
        except Exception:  # self-safe: en defekt behov-funktion tier karakteren
            return None
    return _emne(surf) or f"{ch['id']}:aktiv"


def _stemme(surf: dict[str, Any], ch: dict[str, Any]) -> str:
    """Surfacens EGEN aflæsning.

    Målt 13/11-2026: 14 af 17 surfaces har en `felt` med det konkrete fund.
    Ensemblet brugte den ikke — den viste en hardcodet replik, mens den ægte
    aflæsning blev kastet væk. Det er forskellen på en stemme og en staffage.

    En karakter uden `felt` kan definere sin egen `stemme`-funktion.
    """
    fn = ch.get("stemme")
    if fn is not None:
        try:
            t = str(fn(surf) or "").strip()
            if t:
                return t
        except Exception:  # self-safe: fejler den, falder vi tilbage til felt/statisk linje
            pass
    felt = str(surf.get("felt") or "").strip()
    if not felt:
        summ = surf.get("summary")
        if isinstance(summ, dict):
            felt = str(summ.get("felt") or "").strip()
    return felt or ch["line"]


def _trainman_stemme(surf: dict[str, Any]) -> str:
    """Trainman har ingen `felt` — hans ægte indhold er den nyeste drøm.

    Uden dette ville han altid sige «Drømme ankommer. Erindringer forlader»,
    uanset hvilken drøm han faktisk lige har vævet.
    """
    recent = surf.get("recent")
    if isinstance(recent, list) and recent:
        r = recent[0]
        if isinstance(r, dict):
            narr = str(r.get("narrative") or "").strip()
            if narr:
                return narr
            tema = str(r.get("theme") or "").strip()
            if tema:
                return f"Drømmen i nat handlede om {tema}."
    return ""


def _karakterer_med_behov() -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    """(ch, surf, behov) for hver karakter der lige nu har et uløst behov."""
    ud: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for ch in _CHARACTERS:
        builder = _SURFACE_BUILDERS.get(ch["id"])
        if builder is None:
            continue
        try:
            surf = builder()
        except Exception:  # self-safe: én defekt surface maa ikke draebe de oevrige
            continue
        behov = _behov(ch, surf)
        if behov:
            ud.append((ch, surf, behov))
    return ud


def tick_matrix_lifecycle() -> dict[str, int]:
    """Æld behovet op — og lad karakteren trække sig når den har sagt sit.

    Kaldes ved prompt-build, UAFHÆNGIGT af om karakteren blev vist. Det er hele
    pointen: et behov ældes af at bestå, ikke af at blive nævnt. Derfor kan en
    karakter heller ikke nagle i det uendelige ved at blive ved med at blive vist.
    """
    liv = _load_lifecycle()
    nu = datetime.now(UTC)
    sidst = str(liv.get("_sidst_aldret") or "")
    if sidst:
        try:
            if (nu - datetime.fromisoformat(sidst)).total_seconds() < _ALDRES_MIN_SEKUNDER:
                return {"sprunget_over": 1}
        except Exception:  # self-safe: et ulaeseligt tidsstempel betyder "aldr nu"
            pass

    til_stede: set[str] = set()
    trukket = 0
    for ch, _surf, behov in _karakterer_med_behov():
        cid = ch["id"]
        til_stede.add(cid)
        post = liv.get(cid) if isinstance(liv.get(cid), dict) else {}
        if str(post.get("behov") or "") == behov:
            n = int(post.get("set") or 0) + 1
            sagt = int(post.get("sagt") or 0)
            # (13/11-2026) Et behov må ikke kunne TRÆKKE SIG uden at være blevet
            # hørt. Med 31 karakterer og et loft på nogle få ville de samme altid
            # vinde, og resten ville ældes ud i tavshed — «trukket sig» uden
            # nogensinde at have talt. Derfor kræver tilbagetrækningen mindst ÉN
            # visning: sagt >= 1. Ellers bliver «kom og gå» til «kom aldrig».
            opgivet = bool(post.get("opgivet")) or (n >= _GIV_OP_SEEN and sagt >= 1)
            if opgivet and not post.get("opgivet"):
                trukket += 1
            liv[cid] = {**post, "behov": behov, "set": n, "sagt": sagt, "opgivet": opgivet}
        else:
            liv[cid] = {"behov": behov, "set": 1, "opgivet": False}
    for cid in list(liv):
        if cid != "_sidst_aldret" and cid not in til_stede:
            del liv[cid]
    liv["_sidst_aldret"] = nu.isoformat()
    _save_lifecycle(liv)
    return {"til_stede": len(til_stede), "trukket_sig": trukket, "sporede": len(til_stede)}


def active_character_voices(*, limit: int = _MAX_VOICES) -> list[dict[str, Any]]:
    """De karakterer der har noget at sige LIGE NU. Ren læsning; ingen side-effekter.

    Tilstedeværelse = der findes et uløst behov. Er behovet først sagt, TIER
    karakteren — den gentager ikke den samme sætning mens behovet står stille.
    Har den sagt det i ``_GIV_OP_SEEN`` ture uden at det blev løst, har den
    TRUKKET SIG og kommer ikke igen om det samme emne.

    Rækkefølgen er `_CHARACTERS`-orden (Neo først, Smith nr. to) — de vigtigste
    overlever `limit`. Self-safe: en karakter der kaster springes over.
    """
    liv = _load_lifecycle()
    kandidater: list[tuple[dict[str, Any], dict[str, Any], str, int]] = []
    for ch, surf, behov in _karakterer_med_behov():
        cid = ch["id"]
        post = liv.get(cid) if isinstance(liv.get(cid), dict) else {}
        if str(post.get("behov") or "") == behov:
            if post.get("opgivet"):
                continue        # sagt for længe uden effekt → den er gået
            n = int(post.get("set") or 0)
            if n > 1 and n % _GENTAG_HVER != 0:
                continue        # sagt; tier i mellemrummene og vender tilbage
        kandidater.append((ch, surf, behov, int(post.get("sagt") or 0)))

    # (13/11-2026) RÆKKEFØLGEN ER NU EN RANGERING, IKKE EN INDSÆTTELSESORDEN.
    # Med 31 karakterer og et loft på nogle få betød `_CHARACTERS`-ordenen at
    # Neo og Smith altid vandt, og de fjorten nederst blev aldrig set — men
    # blev alligevel ældet. Nu kommer de mest oversete først: høj ubesvaret-
    # tælling, derefter dem der aldrig har talt, derefter længst ventende.
    kandidater.sort(key=lambda k: (
        -get_unaddressed(k[0]["id"]),
        k[3],
        -int((liv.get(k[0]["id"]) or {}).get("set") or 0),
    ))

    out: list[dict[str, Any]] = []
    for ch, surf, behov, _sagt in kandidater:
        if len(out) >= max(1, int(limit)):
            break
        cid = ch["id"]
        raw = _stemme(surf, ch)
        unaddressed = get_unaddressed(cid)
        out.append({
            "cid": cid,
            "label": ch["label"],
            "line": raw,
            "behov": behov,
            "unaddressed": unaddressed,
            "text": _escalated_message(ch["label"], unaddressed, raw)
            if unaddressed > 0 else f"{ch['label']} {raw}",
        })
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
    # (13/11-2026) At være VIST er ikke at være BESVARET — derfor rører dette kun
    # livscyklussens `sagt`, aldrig `unaddressed`. Uden det ville `sagt` aldrig
    # blive 1, og med reglen om at et behov ikke må trække sig uhørt, kunne ingen
    # karakter nogensinde gå igen.
    _note_sagt([v["cid"] for v in voices])
    return "\n".join(lines)


def _note_sagt(cids: list[str]) -> None:
    """Registrér at karaktererne blev VIS'T — ikke at de blev besvaret."""
    try:
        liv = _load_lifecycle()
        for cid in cids:
            post = liv.get(str(cid))
            if isinstance(post, dict):
                post["sagt"] = int(post.get("sagt") or 0) + 1
        _save_lifecycle(liv)
    except Exception as exc:  # self-safe: livscyklussen er raadgivende, ikke kritisk
        logger.debug("matrix_voice_lifecycle: sagt-registrering fejlede: %s", exc)


def note_voices_shown(cids: list[str]) -> None:
    """Tæl en visning op som ubesvaret. Kaldes EFTER en tur hvor de blev vist.

    Adskilt fra rendering med vilje: at have set en stemme er ikke det samme som at have
    svaret den, og det var netop den sammenblanding der tømte nudge-brønden.

    (13/11-2026) Den tæller også `sagt` i livscyklussen: en karakter der aldrig
    er blevet vist må ikke kunne trække sig som om den havde talt forgæves.
    """
    if not cids:
        return
    liv = _load_lifecycle()
    for cid in cids:
        try:
            increment_unaddressed(str(cid))
        except Exception:  # self-safe: en fejlet optaelling maa ikke stoppe de oevrige
            continue
        post = liv.get(str(cid))
        if isinstance(post, dict):
            post["sagt"] = int(post.get("sagt") or 0) + 1
    try:
        _save_lifecycle(liv)
    except Exception as exc:  # self-safe: livscyklussen er raadgivende, ikke kritisk
        logger.debug("matrix_voice_lifecycle: sagt-gemning fejlede: %s", exc)


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
