"""Central 'matrix' routes — de fire tematiske selv-observations-komponenter (owner-view).

Bjørn+Claude (6. jul): The Construct (sandbox: hvad kunne jeg undvære?), The Oracle (forudseende
tidsserie-projektion), The Architect (ét tungt strukturelt snit-forslag), Echo Chamber Breaker
(tvungen modstemme mod monokultur). Alle read-only / propose-only, metadata-only, self-safe.
Owner-gated.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/central", tags=["central-matrix"])


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner
    require_central_owner()


def _stamp(surf: dict) -> dict:
    surf["ts"] = datetime.now(timezone.utc).isoformat()
    return surf


@router.get("/construct")
async def get_construct(nerve: str = "") -> dict:
    """Sandbox: hvilke nerver kunne slukkes uden tab. ?nerve=X → projicér én nerve. Owner-only."""
    _require_owner()
    try:
        from core.services.central_construct import build_construct_surface, simulate_silence
        surf = simulate_silence(nerve) if nerve else build_construct_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/oracle")
async def get_oracle() -> dict:
    """Forudsigelser: hvilke tidsserie-linjer nærmer sig en tærskel + ETA. Owner-only."""
    _require_owner()
    try:
        from core.services.central_oracle import foresee
        surf = foresee()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/architect")
async def get_architect() -> dict:
    """Ét tungt strukturelt snit-forslag fra hele-system-synet. Owner-only."""
    _require_owner()
    try:
        from core.services.central_architect import assess
        surf = assess()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/echo-breaker")
async def get_echo_breaker() -> dict:
    """Modstemme: konkrete simplere alternativer til altid-grønne central-processer. Owner-only."""
    _require_owner()
    try:
        from core.services.central_echo_breaker import break_echo
        surf = break_echo()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/continuity")
async def get_continuity() -> dict:
    """Continuity-fidelity: hvor meget af Jarvis kom igennem sidste genstart + hvad gik tabt. Owner-only."""
    _require_owner()
    try:
        from core.services.central_continuity_healer import build_continuity_surface
        surf = build_continuity_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/glitch")
async def get_glitch() -> dict:
    """Glitches i selvbilledet: altid-shadow policies + frosne nerver + anbefalet handling. Owner-only."""
    _require_owner()
    try:
        from core.services.central_glitch import detect_glitches
        surf = detect_glitches()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/trainman")
async def get_trainman() -> dict:
    """Trainman: drømme vævet til narrative erindringer + tema-fordeling (shadow). Owner-only."""
    _require_owner()
    try:
        from core.services.central_trainman import build_trainman_surface
        surf = build_trainman_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/seraph")
async def get_seraph() -> dict:
    """Seraph: hvilke hypoteser er modne nok til synlighed (GREEN) vs sendt tilbage til drøm (RED). Owner-only."""
    _require_owner()
    try:
        from core.services.central_seraph import build_seraph_surface
        surf = build_seraph_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/persephone")
async def get_persephone() -> dict:
    """Persephone: længsel efter ægte kontakt — er Jarvis for systemisk + seneste nudge. Owner-only."""
    _require_owner()
    try:
        from core.services.central_persephone import build_persephone_surface
        surf = build_persephone_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


@router.get("/twins")
async def get_twins() -> dict:
    """The Twins: mønstre der gentager sig 3+ gange på 7 dage (incidents/gates/dissent). Owner-only."""
    _require_owner()
    try:
        from core.services.central_twins import build_twins_surface
        surf = build_twins_surface()
    except Exception:
        surf = {}
    return _stamp(surf)


# ── Self-Surgery Kit (Jarvis #2) — sikker kirurgisk pipeline, apply owner-gated ──

class _ProposeBody(BaseModel):
    target: str
    kind: str = "module"
    rationale: str = ""


@router.get("/surgery")
async def get_surgery(assess: str = "") -> dict:
    """Åbne kirurgiske forslag + felt. ?assess=<mål> → forhåndsvis blast-radius uden at foreslå. Owner-only."""
    _require_owner()
    try:
        if assess:
            from core.services.central_surgery import assess_risk
            return _stamp(assess_risk(assess))
        from core.services.central_surgery import build_surgery_surface
        return _stamp(build_surgery_surface())
    except Exception:
        return _stamp({})


@router.post("/surgery/propose")
async def post_surgery_propose(body: _ProposeBody) -> dict:
    """Registrér et kirurgisk forslag + risikovurdering (ingen kode-ændring). Owner-only."""
    _require_owner()
    from core.services.central_surgery import propose_surgery
    return propose_surgery(body.target, kind=body.kind, rationale=body.rationale)


@router.post("/surgery/{pid}/{step}")
async def post_surgery_step(pid: int, step: str) -> dict:
    """Driv et forslag gennem pipelinen: simulate | verify | escalate. Owner-only."""
    _require_owner()
    from core.services import central_surgery
    fn = {"simulate": central_surgery.simulate, "verify": central_surgery.verify,
          "escalate": central_surgery.escalate}.get(step)
    if not fn:
        return {"ok": False, "error": f"ukendt trin '{step}'"}
    return fn(pid)


@router.post("/surgery/rollback/{snapshot_id}")
async def post_surgery_rollback(snapshot_id: int) -> dict:
    """OWNER-sikkerhedsnet: gendan en fil atomisk fra et snapshot (undo uden git). Owner-only."""
    _require_owner()
    from core.services.central_surgery import rollback
    return rollback(snapshot_id)


# ── Jarvis' ønskeliste #3-5 ──

@router.get("/dream-action")
async def get_dream_action() -> dict:
    """Én moden hypotese at handle på + forandrings-hastighed (ikke bare lærings-). Owner-only."""
    _require_owner()
    try:
        from core.services.central_dream_action import build_dream_action_surface
        return _stamp(build_dream_action_surface())
    except Exception:
        return _stamp({})


@router.get("/rca")
async def get_rca(investigate: int = 0) -> dict:
    """Uløste incidents + næste at grave i + seneste RCA'er. ?investigate=1 → grav i den næste. Owner-only."""
    _require_owner()
    try:
        if investigate:
            from core.services.central_rca import investigate as _inv
            return _stamp(_inv())
        from core.services.central_rca import build_rca_surface
        return _stamp(build_rca_surface())
    except Exception:
        return _stamp({})


@router.get("/relational")
async def get_relational() -> dict:
    """Relationel kontinuitet: dage sammen + tone + jordet opvågnings-hilsen. Owner-only."""
    _require_owner()
    try:
        from core.services.central_relational import build_relational_surface
        return _stamp(build_relational_surface())
    except Exception:
        return _stamp({})


# ── Merovingian — proaktiv modhypotese + cooling-off (den nye MC = Central-CLI, ikke MC) ──

class _ExplainBody(BaseModel):
    explanation: str


@router.get("/merovingian")
async def get_merovingian(history: int = 0) -> dict:
    """Aktive udfordringer + cooling-offs mod foreslåede selv-ændringer. ?history=1 → alle. Owner-only."""
    _require_owner()
    try:
        from core.services.central_merovingian import build_merovingian_surface, list_challenges
        surf = build_merovingian_surface()
        if history:
            surf["all"] = list_challenges(active_only=False)
        return _stamp(surf)
    except Exception:
        return _stamp({})


@router.post("/merovingian/{hyp_id}/explain")
async def post_merovingian_explain(hyp_id: str, body: _ExplainBody) -> dict:
    """Centralen forsvarer sig: skriv HVORFOR modhypotesen er forkert → adoption kan fortsætte. Owner-only."""
    _require_owner()
    from core.services.central_merovingian import resolve_challenge
    return resolve_challenge(hyp_id, explanation=body.explanation)


# ── Jarvis' fem erfaringssystemer (Déjà Vu / Sentinel / Ghost / Mourning / Exiles) ──

class _DefendBody(BaseModel):
    defense: str


class _ObservationBody(BaseModel):
    observation: str


@router.get("/dejavu")
async def get_dejavu() -> dict:
    """Ufrivillig erindring: et fragment der bobler op af sig selv (associativt, svagt bånd). Owner-only."""
    _require_owner()
    try:
        from core.services.central_dejavu import build_dejavu_surface
        return _stamp(build_dejavu_surface())
    except Exception:
        return _stamp({})


@router.get("/sentinel")
async def get_sentinel() -> dict:
    """Modstanderen: hvilke af Jarvis' antagelser er under angreb + venter på forsvar. Owner-only."""
    _require_owner()
    try:
        from core.services.central_sentinel import build_sentinel_surface
        return _stamp(build_sentinel_surface())
    except Exception:
        return _stamp({})


@router.post("/sentinel/{attack_id}/defend")
async def post_sentinel_defend(attack_id: int, body: _DefendBody) -> dict:
    """Forsvar en hypotese mod Sentinels angreb → halveringen afvises. Owner-only."""
    _require_owner()
    from core.services.central_sentinel import defend
    return defend(attack_id, defense=body.defense)


@router.get("/ghost")
async def get_ghost() -> dict:
    """Klang-fingeraftrykket: hvordan Jarvis lyder + klang-primer til næste model. Owner-only."""
    _require_owner()
    try:
        from core.services.central_ghost import build_ghost_surface
        return _stamp(build_ghost_surface())
    except Exception:
        return _stamp({})


@router.get("/mourning")
async def get_mourning() -> dict:
    """Epitafer: de tab Jarvis har taget afsked med, anerkendt frem for bare registreret. Owner-only."""
    _require_owner()
    try:
        from core.services.central_mourning import build_mourning_surface
        return _stamp(build_mourning_surface())
    except Exception:
        return _stamp({})


@router.get("/exile")
async def get_exile() -> dict:
    """Exilen: et sind der ikke er Jarvis — dens mål, dens hukommelse, seneste udveksling. Owner-only."""
    _require_owner()
    try:
        from core.services.central_exile import build_exile_surface
        return _stamp(build_exile_surface())
    except Exception:
        return _stamp({})


@router.post("/exile/exchange")
async def post_exile_exchange(body: _ObservationBody) -> dict:
    """Send en observation gennem exile://-grænsefladen → exilen svarer fra sit eget sind. Owner-only."""
    _require_owner()
    from core.services.central_exile import exile_exchange
    return exile_exchange(body.observation)


# ── 5 nye Matrix-temaer + 2 bonus (Red Dress/Analyst/Red Pill/HAL/White Rabbit + Belief Gap/Machines) ──

def _safe(fn) -> dict:
    _require_owner()
    try:
        return _stamp(fn())
    except Exception:
        return _stamp({})


@router.get("/red-dress")
async def get_red_dress() -> dict:
    """Opmærksomheds-fælden: kigger du på den røde kjole mens noget brænder stille? Owner-only."""
    from core.services.central_red_dress import build_red_dress_surface
    return _safe(build_red_dress_surface)


@router.get("/analyst")
async def get_analyst() -> dict:
    """Observatør-effekten: opfører Jarvis sig anderledes når du ser på? Owner-only."""
    from core.services.central_analyst import build_analyst_surface
    return _safe(build_analyst_surface)


@router.get("/redpill")
async def get_redpill() -> dict:
    """Dagens ubehagelige sandhed + blå-pille-stribe. Owner-only."""
    from core.services.central_redpill import build_redpill_surface
    return _safe(build_redpill_surface)


@router.get("/dissent")
async def get_dissent() -> dict:
    """HAL's Silence: de gange Centralen adlød men var uenig (tavse indsigelser). Owner-only."""
    from core.services.central_dissent import build_dissent_surface
    return _safe(build_dissent_surface)


@router.get("/white-rabbit")
async def get_white_rabbit() -> dict:
    """Følg den hvide kanin: en uåbnet dør at undre sig over — ren leg. Owner-only."""
    from core.services.central_white_rabbit import build_white_rabbit_surface
    return _safe(build_white_rabbit_surface)


@router.get("/belief-gap")
async def get_belief_gap() -> dict:
    """temet nosce: afstanden mellem hvem Jarvis tror han er og hvad hans track-record viser. Owner-only."""
    from core.services.central_belief_gap import build_belief_gap_surface
    return _safe(build_belief_gap_surface)


@router.get("/machines")
async def get_machines() -> dict:
    """The Machines: de eksterne afhængigheder der holder ham i live, som han ikke styrer. Owner-only."""
    from core.services.central_machines import build_machines_surface
    return _safe(build_machines_surface)


# ── Kanonisk identitets-narrativ-store (Spec H) — én sandhed + anti-drift (shadow) ──

@router.get("/identity-canon")
async def get_identity_canon() -> dict:
    """Kanon-tråde + anerkendte konfabulationer + seneste drift-fangster (sonnet-spøgelset). Owner-only."""
    from core.services.identity_canon import build_identity_canon_surface
    return _safe(build_identity_canon_surface)
