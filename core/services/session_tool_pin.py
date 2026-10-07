"""Fastlås tool-sættet pr. session, så prompt-præfikset holder (2026-09-05).

Målt på Bjørns konto: 14 ture i træk fik hver sit nye præfiks-sha, og præfikset
er 80-100.000 tegn. Årsagen er tool-routeren: den vælger en ny delmængde ud fra
hver besked — journalen for 4. september viser 58, 59, 61, 80, 81, 82, 83, 84,
85, 86, 87 og 88 værktøjer på forskellige ture. Tools-arrayet ligger LIGE EFTER
systembeskeden i DeepSeeks template, så et nyt sæt bryder cachen præcis dér, og
hele historikken bagefter (op til 160k tokens) betales fuldt hver eneste tur.

Symptomet i hovedbogen er umiskendeligt: `cache_hit_tokens` fryser på 6.400-8.320
— nøjagtig systembeskedens længde — mens `cache_miss_tokens` vokser lineært med
samtalen: 13k → 38k → 50k → 76k den 4. september.

Inden i ÉN tur var tools allerede byte-stabile (fixet 30/6), og dér måles 86 %
hit. Det er kun på tværs af ture at sættet skifter.

Løsningen er ikke at droppe routeren — færre værktøjer giver bedre fokus — men
at lade den bestemme ÉN gang pr. session i stedet for hver tur:

* første tur i en session router som før, og sættet gemmes;
* efterfølgende ture genbruger det, så præfikset er byte-identisk;
* `load_more_tools` udvider låsen, så tilføjelser holder ved til næste tur i
  stedet for at forsvinde;
* låsen nulstilles ved compaction, hvor historikken alligevel skrives om og
  cachen brydes — så routeren får frisk indflydelse uden at koste noget ekstra.

Kill-switch: `settings.session_tool_pin_enabled = False` → routeren kører pr.
tur igen, præcis som før.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_KEY_PREFIX = "session_tool_pin:"
_MAX_NAMES = 400


def pin_enabled() -> bool:
    """Er låsen slået til? Fail-safe: enhver fejl → til (den nye adfærd)."""
    try:
        from core.runtime.settings import load_settings
        return bool(getattr(load_settings(), "session_tool_pin_enabled", True))
    except Exception:
        return True


def _key(session_id: str) -> str:
    return f"{_KEY_PREFIX}{str(session_id or '').strip()}"


def _compact_epoch(session_id: str) -> int:
    """Compaction-markøren for sessionen. Skifter den, er historikken skrevet
    om og cachen brudt alligevel — så må routeren gerne vælge forfra."""
    try:
        from core.context.tool_result_lifecycle import latest_compact_marker_id
        return int(latest_compact_marker_id(str(session_id or "")) or 0)
    except Exception:
        return 0


def _state_get(session_id: str) -> dict[str, Any]:
    try:
        from core.runtime.db import get_runtime_state_value
        raw = get_runtime_state_value(_key(session_id), None)
        return dict(raw) if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _state_set(session_id: str, payload: dict[str, Any]) -> None:
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_key(session_id), payload)
    except Exception as exc:
        logger.debug("session_tool_pin: kunne ikke gemme laas: %s", exc)


def get_pinned(session_id: str) -> list[str]:
    """Det låste sæt for sessionen — tom liste når intet er låst, eller når
    compaction har flyttet epoken siden låsen blev sat."""
    sid = str(session_id or "").strip()
    if not sid or not pin_enabled():
        return []
    state = _state_get(sid)
    names = [str(n) for n in (state.get("names") or []) if str(n).strip()]
    if not names:
        return []
    if int(state.get("epoch") or 0) != _compact_epoch(sid):
        return []
    return names


def pin(session_id: str, names: list[str]) -> list[str]:
    """Lås sættet for sessionen. Returnerer det låste sæt."""
    sid = str(session_id or "").strip()
    clean = sorted({str(n).strip() for n in (names or []) if str(n).strip()})[:_MAX_NAMES]
    if not sid or not clean or not pin_enabled():
        return clean
    _state_set(sid, {"names": clean, "epoch": _compact_epoch(sid)})
    return clean


def extend(session_id: str, names: list[str]) -> list[str]:
    """Udvid låsen (load_more_tools). Tilføjelser holder ved til næste tur."""
    sid = str(session_id or "").strip()
    extra = {str(n).strip() for n in (names or []) if str(n).strip()}
    if not sid or not extra or not pin_enabled():
        return get_pinned(sid)
    current = set(get_pinned(sid))
    if not current:
        return []           # intet låst endnu — næste tur låser hele sættet
    if extra <= current:
        return sorted(current)
    return pin(sid, sorted(current | extra))


def clear(session_id: str) -> None:
    _state_set(str(session_id or "").strip(), {})


def _med_garanterede(navne: list[str]) -> list[str]:
    """Foren med de vaerktoejer der ALTID skal kunne kaldes — og sorter.

    `REQUIRED_LAZY_TOOL_NAMES` er listen hvis formaal er «maa altid overleve
    kappen»; `SAFETY_FLOOR` er de vaerktoejer hvis fravaer er en
    adfaerdsregression. Begge er KONSTANTE, saa arrayet er stadig byte-stabilt
    fra tur til tur — og sorteringen er ikke kosmetik: raekkefoelgen ER
    cache-noeglen, saa samme saet i to raekkefoelger er to praefikser.

    Self-sikker: kan listerne ikke importeres, returneres navnene uaendret.
    En forening der kaster ville braekke hvert vaerktoejskald.
    """
    try:
        from core.tools.copilot_tool_pruning import (
            REQUIRED_LAZY_TOOL_NAMES,
            SAFETY_FLOOR,
        )
    except Exception as exc:  # en forening maa ikke braekke tool-stien
        logger.debug("session_tool_pin: kunne ikke hente de garanterede: %s", exc)
        return sorted(set(navne))
    try:
        from core.tools.copilot_tool_pruning import agent_contract_pinned
        agent = set(agent_contract_pinned())
    except Exception as exc:  # samme regel: en forening maa ikke braekke tool-stien
        logger.debug("session_tool_pin: kunne ikke hente agent-vaerktoejerne: %s", exc)
        agent = set()
    return sorted(set(navne) | set(REQUIRED_LAZY_TOOL_NAMES) | set(SAFETY_FLOOR) | agent)


def resolve(
    session_id: str,
    selected_names: list[str],
    extra_required: tuple[str, ...] = (),
) -> tuple[list[str], str]:
    """Hvilke værktøjer skal denne tur sende?

    Returnerer (navne, kilde) hvor kilde er "pinned" (genbrugt, præfiks holder),
    "pinned-new" (denne tur låste sættet) eller "router" (låsen er slået fra).
    Self-safe: enhver fejl → routerens eget valg, som før.

    ``extra_required`` er værktøjer der er nødvendige netop fordi prompten
    nævner dem — i praksis ``skill_invoke`` når et skill matcher (2/10-2026).
    De flettes ind i LÅSEN, ikke kun i svaret, så arrayet står stille fra næste
    tur af. Uden det nåede den betingede pin kun første pas, og de agentiske
    runder — hvor arbejdet sker — havde intet skill-værktøj overhovedet.
    """
    sid = str(session_id or "").strip()
    picked = [str(n) for n in (selected_names or []) if str(n).strip()]
    ekstra = [str(n).strip() for n in (extra_required or []) if str(n).strip()]
    if not sid or not picked or not pin_enabled():
        return picked, "router"
    try:
        existing = get_pinned(sid)
        if existing:
            # ── Laasen maa ikke laase de KRAEVEDE ude (30/9-2026) ──────────
            #
            # `existing` blev sat én gang og returneres derefter i stedet for
            # routerens valg. Alt der bliver noedvendigt SENERE naaede derfor
            # aldrig frem — laasen nulstilles foerst ved compaction.
            #
            # Maalt samme dag: en session havde 97 laaste vaerktoejer, og
            # `call_loaded_tool` var IKKE blandt dem, fordi den blev bygget
            # efter laasen blev sat. Modellen kunne dermed ikke kalde den
            # overhovedet — adoptionen var nul af den grund, ikke fordi den
            # blev fravalgt. `notify_user` manglede paa samme vis og blev
            # hentet 20 gange paa 30 dage.
            #
            # Foreningen er med de EKSPLICIT kraevede — ikke med hele kernen.
            # `REQUIRED_LAZY_TOOL_NAMES` er den liste hvis hele formaal er «maa
            # altid overleve kappen», og den er konstant, saa arrayet er stadig
            # byte-stabilt fra tur til tur. Sorteret af samme grund.
            #
            # Prisen er ét cache-brud i de sessioner der mangler noget: arrayet
            # aendrer sig én gang, og derefter staar det stille igen. Et
            # vaerktoej der ikke kan kaldes er dyrere end det brud.
            if ekstra and not set(ekstra) <= set(existing):
                # Et betinget krævet værktøj nåede ikke låsen. Foreningen sker
                # ÉN gang — derefter står arrayet stille igen, så præfikset
                # holder. Samme afvejning som `_med_garanterede`: et værktøj
                # der ikke kan kaldes er dyrere end ét cache-brud.
                return _med_garanterede(pin(sid, [*existing, *ekstra])), "pinned"
            return _med_garanterede(existing), "pinned"
        # FOERSTE tur i sessionen. Foreningen skal ogsaa gaelde HER: uden den
        # var de garanterede vaerktoejer fravaerende praecis paa den tur der
        # laaser saettet — og saa manglede de i hele sessionens levetid.
        # Det er samtidig aabneren, som baerer ~35 % af al cache-miss.
        pin(sid, [*picked, *ekstra])
        return _med_garanterede([*picked, *ekstra]), "pinned-new"
    except Exception as exc:
        logger.debug("session_tool_pin: resolve faldt tilbage til routeren: %s", exc)
        return picked, "router"


def build_session_tool_pin_surface(session_id: str = "") -> dict[str, Any]:
    names = get_pinned(session_id) if session_id else []
    return {
        "active": bool(names),
        "enabled": pin_enabled(),
        "count": len(names),
        "summary": (
            f"{len(names)} vaerktoejer laast for sessionen"
            if names else "intet laast (routeren vaelger)"
        ),
    }
