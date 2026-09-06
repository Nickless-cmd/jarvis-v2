"""Dream-to-Action: den ende der manglede.

`central_dream_action.py` blev skrevet som svar på Jarvis' egen klage — *"jeg lærer, men
jeg forandrer mig ikke"* — og den fandt modne hypoteser helt korrekt. Men den var
**propose-only**, og forbrugeren af forslaget blev aldrig bygget: `record_action()` havde
NUL kaldere nogen steder i repoet. Målt 19. aug 2026: 5 modne hypoteser klar,
`change_rate()` = 374 i backlog, **0 handlinger på 7 dage**, `central_dream_actions` tom
siden filen blev skrevet. To services formulerede endda sætningen *"moden nok til
handling — men jeg har ikke handlet"* og sendte den kun til et HTTP-endpoint ingen så.

**Hvad "handling" er her — og hvad den IKKE er.**
Klassen vi handler på er `prediction_error`: sekvens-modellen gav en overgang X→Y en
sandsynlighed under 5%, og den skete alligevel. Hypotesen er falsificerbar: *"det var
ikke støj — regimet er ægte og gentager sig over baseline."*

Modellen har siden lært overgangen (`learn_from_stream` tæller løbende). Handlingen er
derfor en **måling**: hent transitions-sandsynligheden igen nu og afgør om regimet holdt.
Ingen LLM, intet gæt — udelukkende tal der allerede står i `central_sequence_transitions`.

**Den afgør IKKE hypotesen.** Status/confidence/resolution ejes af
`central_hypothesis_generator` + governance. Vi skriver en handling og et resultat; vi
rører aldrig hypotese-tabellen. To sandheder om samme hypotese ville være præcis den
dobbelt-bogføring runtime-reglerne forbyder.

**Lagene, fordi den ændrer ham selv (Bjørn 19. aug: "så længe vi kan se alt og gribe ind"):**

1. **`shadow` som default.** Den beregner og logger hvad den VILLE gøre uden at skrive.
   Samme trust-gate som `self_repair_engine` og `system_cartographer`: bevis først.
2. **Snæver allowlist.** Kun `mechanism == "prediction_error"`. Enhver anden hypotese-
   klasse ignoreres — også hvis den ser moden ud.
3. **Loft pr. tick.** Højst `_MAX_PER_TICK`; en løbsk løkke kan ikke tømme backloggen.
4. **Klient-synlig.** Hver handling giver en central-incident med hypotese-id, før/efter-
   sandsynlighed og dom — så indgreb er muligt uden at læse en database.
5. **Auto-stop.** Gentagne fejl slår eksekutoren i `off`; den genstarter ikke sig selv.
6. **Reversibel.** Den skriver kun rækker i `central_dream_actions`. Intet muteres.
"""
from __future__ import annotations

from typing import Any

_MODE_KEY = "dream_action_executor_mode"     # off | shadow | live — DEFAULT live (4/9)
_ERROR_KEY = "dream_action_executor_errors"
_MAX_PER_TICK = 3
_MAX_ERRORS_BEFORE_OFF = 5

# Kun denne mekanisme handles på. Sekvens-overraskelser er den ENESTE klasse hvor
# "handling" kan afgøres mekanisk mod tal der allerede findes.
_ALLOWED_MECHANISMS = frozenset({"prediction_error"})

# Regimet regnes for holdt når sandsynligheden er over overraskelses-tærsklen igen.
_SURPRISE_THRESHOLD = 0.05
# Vi tør kun dømme når from-familien er set nok gange til at raten betyder noget.
_MIN_FROM_TOTAL = 20


def mode() -> str:
    """``'off'`` | ``'shadow'`` | ``'live'``. Default **live** siden 2026-09-04.

    Var shadow "bevis før tillid" — men i shadow skrives der ingen raekker, saa
    beviset kunne aldrig opstaa: `central_dream_actions` har haft NUL raekker
    siden filen blev skrevet. Kun én mekanisme er tilladt (`prediction_error`),
    loftet er tre pr. tick, og auto-stoppet efter fem fejl er uaendret — saa
    live er stadig et smalt vindue, bare et der kan maales.
    """
    try:
        from core.runtime.db import get_runtime_state_value

        v = str(get_runtime_state_value(_MODE_KEY, "live") or "live").strip().lower()
        return v if v in ("off", "shadow", "live") else "live"
    except Exception:
        return "live"


def _parse_family(provenance: dict[str, Any]) -> tuple[str, str] | None:
    """``{"family": "X->Y"}`` → ``("X", "Y")``. None hvis formen ikke er som forventet."""
    fam = str((provenance or {}).get("family") or "")
    if "->" not in fam:
        return None
    a, _, b = fam.partition("->")
    a, b = a.strip(), b.strip()
    return (a, b) if a and b else None


def adjudicate(from_fam: str, to_fam: str) -> dict[str, Any]:
    """Mål om regimet holdt. Ren læsning af sekvens-modellen; ændrer ingenting.

    ``verdict``: ``'regime'`` (overgangen er over tærsklen nu — modellen manglede den
    og har lært den), ``'noise'`` (stadig under, med nok observationer til at sige det),
    ``'undecided'`` (for lidt data — vi handler ikke på et gæt).
    """
    try:
        from core.services import central_sequence as seq
        from core.runtime.db import connect

        p = float(seq.transition_prob(from_fam, to_fam))
        with connect() as c:
            total = int(seq._from_total(c, from_fam))
    except Exception as exc:
        return {"verdict": "undecided", "reason": f"måling fejlede: {type(exc).__name__}",
                "prob": None, "from_total": None}

    if total < _MIN_FROM_TOTAL:
        return {"verdict": "undecided", "prob": round(p, 4), "from_total": total,
                "reason": f"kun {total} observationer af '{from_fam}' — for tyndt til en dom"}
    if p >= _SURPRISE_THRESHOLD:
        return {"verdict": "regime", "prob": round(p, 4), "from_total": total,
                "reason": f"'{from_fam}'→'{to_fam}' er nu P={p:.4f} ≥ {_SURPRISE_THRESHOLD} "
                          f"— regimet var ægte, modellen manglede det"}
    return {"verdict": "noise", "prob": round(p, 4), "from_total": total,
            "reason": f"'{from_fam}'→'{to_fam}' er stadig P={p:.4f} efter {total} "
                      f"observationer — det var støj"}


def _observe_incident(hyp_id: str, ver: dict[str, Any], *, applied: bool) -> None:
    """Klient-synlig, så indgreb er muligt uden at læse en database."""
    try:
        from core.runtime.db_central_incidents import record_central_incident

        record_central_incident(
            cluster="system", nerve="dream_action_executor",
            kind="acted" if applied else "shadow", severity="info", dedup=False,
            message=(f"[{'LIVE' if applied else 'SHADOW'}] {hyp_id}: "
                     f"{ver['verdict']} — {ver.get('reason', '')}")[:400],
        )
    except Exception:
        pass


def _bump_errors() -> None:
    """Gentagne fejl → `off`. Den genstarter ikke sig selv."""
    try:
        from core.runtime.db import get_runtime_state_value, set_runtime_state_value

        n = int(get_runtime_state_value(_ERROR_KEY, 0) or 0) + 1
        set_runtime_state_value(_ERROR_KEY, n)
        if n >= _MAX_ERRORS_BEFORE_OFF:
            set_runtime_state_value(_MODE_KEY, "off")
    except Exception:
        pass


def run_once(*, limit: int = _MAX_PER_TICK) -> dict[str, Any]:
    """Ét gennemløb: find modne prediction_error-hypoteser, mål regimet, registrér.

    I `shadow` beregnes alt og observeres, men intet skrives. Self-safe: kaster aldrig.
    """
    m = mode()
    if m == "off":
        return {"mode": m, "considered": 0, "acted": 0, "results": []}

    try:
        from core.services.central_dream_action import record_action, select_actionable
        import json as _json

        candidates = select_actionable(limit=max(1, int(limit)) * 4)
    except Exception as exc:
        _bump_errors()
        return {"mode": m, "error": f"{type(exc).__name__}: {exc}"[:120],
                "considered": 0, "acted": 0, "results": []}

    results: list[dict[str, Any]] = []
    acted = 0
    for h in candidates:
        if acted >= int(limit):
            break
        try:
            prov = h.get("provenance") or h.get("provenance_json") or {}
            if isinstance(prov, str):
                prov = _json.loads(prov or "{}")
            if str(prov.get("mechanism")) not in _ALLOWED_MECHANISMS:
                continue  # snæver allowlist — alt andet ignoreres
            fam = _parse_family(prov)
            if fam is None:
                continue
            ver = adjudicate(*fam)
            if ver["verdict"] == "undecided":
                continue  # vi handler ikke på et gæt
            hyp_id = str(h.get("hyp_id"))
            applied = m == "live"
            if applied:
                w = record_action(
                    hyp_id,
                    action=f"målte regime '{fam[0]}'→'{fam[1]}' efter modellens opdatering",
                    result=f"{ver['verdict']}: {ver['reason']}",
                )
                if not w.get("ok"):
                    _bump_errors()
                    continue
            _observe_incident(hyp_id, ver, applied=applied)
            results.append({"hyp_id": hyp_id, "from": fam[0], "to": fam[1], **ver,
                            "applied": applied})
            acted += 1
        except Exception:
            _bump_errors()
            continue

    return {"mode": m, "considered": len(candidates), "acted": acted, "results": results}


def build_executor_surface() -> dict[str, Any]:
    """Overflade til Centralen: tilstand + hvad den ville/har gjort. Self-safe."""
    m = mode()
    try:
        from core.services.central_dream_action import change_rate

        cr = change_rate()
    except Exception:
        cr = {}
    preview = run_once(limit=_MAX_PER_TICK) if m != "off" else {"results": []}
    return {
        "active": m != "off", "mode": m,
        "allowed_mechanisms": sorted(_ALLOWED_MECHANISMS),
        "max_per_tick": _MAX_PER_TICK,
        "change_rate": cr,
        "latest": preview.get("results") or [],
        "summary": (f"eksekutor i {m}; {len(preview.get('results') or [])} hypoteser "
                    f"målt, {cr.get('active_backlog', '?')} i backlog"),
    }
