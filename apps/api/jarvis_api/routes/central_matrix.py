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
