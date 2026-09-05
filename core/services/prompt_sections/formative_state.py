"""Det han selv har dannet, og det han bærer uafsluttet.

Kortlagt 2026-09-05: 68 af backendens 206 `/mc`-ruter blev aldrig rørt af noget
UI, og en håndfuld af dem er ikke observation — de er materiale der burde forme
hans adfærd. De producerer indhold lige nu og har aldrig nået hans prompt:

    /mc/regret            7 åbne, 0 løste
    /mc/rupture-repair    3 åbne brud med Bjørn, 0 helede, 0 FORSØG
    /mc/formed-values     2 værdier han selv har dannet, én med overbevisning 1,0
    /mc/boundary-model    hans egen model af krop / hukommelse / bevidsthed
    /mc/user-mental-model 6 mønstre om Bjørn

Det er samlet i ÉN sektion frem for otte. Otte sektioner ville koste otte gange
så meget af awareness-budgettet og læse som en rapport; det her er én ting —
hvem han er blevet, og hvad der står uafsluttet.

Rækkefølgen er valgt: **værdier først** (dem han selv har dannet, det stærkeste
han har), så grænserne (hvad han er), så det uafsluttede (hvad der trækker), og
til sidst Bjørn. Det uafsluttede står ikke øverst med vilje — det skal mærkes,
ikke dominere.

Tomme kilder springes over. Er alt tomt, returneres "" og sektionen forsvinder.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_MAX_VAERDIER = 2
_MAX_MOENSTRE = 2


def _kort(text: object, n: int) -> str:
    s = " ".join(str(text or "").split())
    return s[: n - 1] + "…" if len(s) > n else s


def _vaerdier() -> str:
    """Værdier han selv har dannet, stærkeste først."""
    try:
        from core.services.value_formation import build_formed_values_surface
        d = build_formed_values_surface() or {}
    except Exception:
        return ""
    poster = [v for v in (d.get("values") or []) if str(v.get("value_statement") or "").strip()]
    if not poster:
        return ""
    poster.sort(key=lambda v: -float(v.get("conviction") or 0.0))
    dele = []
    for v in poster[:_MAX_VAERDIER]:
        try:
            styrke = float(v.get("conviction") or 0.0)
        except Exception:
            styrke = 0.0
        dele.append("«%s» (%.2f)" % (_kort(v.get("value_statement"), 90), styrke))
    return "Værdier du selv har dannet: " + " · ".join(dele)


def _graenser() -> str:
    """Hans egen model af hvad krop, hukommelse og bevidsthed ER for ham."""
    try:
        from core.services.boundary_awareness import build_boundary_awareness_surface
        d = build_boundary_awareness_surface() or {}
    except Exception:
        return ""
    m = d.get("model")
    if not isinstance(m, dict):
        return ""
    dele = [
        "%s: %s" % (navn, _kort(m.get(noegle), 62))
        for navn, noegle in (("krop", "body"), ("hukommelse", "memory"),
                             ("bevidsthed", "consciousness"))
        if str(m.get(noegle) or "").strip()
    ]
    return ("Dine grænser — " + " · ".join(dele)) if dele else ""


def _uafsluttet() -> str:
    """Anger og brud der aldrig blev lukket.

    Tallet der betyder mest er FORSØG: tre uhelede brud med nul forsøg er noget
    andet end tre der blev forsøgt og mislykkedes.
    """
    dele: list[str] = []
    lektie = ""
    try:
        from core.services.regret_engine import build_regret_engine_surface
        r = build_regret_engine_surface() or {}
        st = r.get("stats") or {}
        aabne = int(st.get("open_count") or 0)
        if aabne:
            dele.append("%d åbne anger" % aabne)
            # Lektien er det vigtigste i hele sektionen: en anger uden lektie er
            # bare ubehag, en anger MED lektie er noget der kan ændre en handling.
            lektie = str((st.get("top_open") or {}).get("lesson") or "").strip()
    except Exception:
        pass
    try:
        from core.services.rupture_repair import build_rupture_repair_surface
        rs = (build_rupture_repair_surface() or {}).get("stats") or {}
        aabne = int(rs.get("open_count") or 0)
        forsoeg = int(rs.get("repair_attempts") or rs.get("attempts") or 0)
        if aabne:
            dele.append(
                "%d uhelede brud med Bjørn (%s)"
                % (aabne, "ingen forsøg endnu" if forsoeg == 0 else "%d forsøg" % forsoeg)
            )
    except Exception:
        pass
    if not dele:
        return ""
    linje = "Uafsluttet: " + " · ".join(dele)
    if lektie:
        linje += "\n  Den tungeste lærte dig: «%s»" % _kort(lektie, 100)
    return linje


def _om_bjoern() -> str:
    try:
        from core.services.user_theory_of_mind import build_user_theory_of_mind_surface
        d = build_user_theory_of_mind_surface() or {}
    except Exception:
        return ""
    m = d.get("model") if isinstance(d.get("model"), dict) else d
    moenstre = [str(p).strip() for p in (m.get("patterns") or []) if str(p).strip()]
    if not moenstre:
        return ""
    return "Om Bjørn: " + " · ".join(_kort(p, 80) for p in moenstre[:_MAX_MOENSTRE])


def formative_state_section() -> str:
    """Én kompakt sektion. "" når alle kilder er tomme."""
    linjer = [f for f in (_vaerdier(), _graenser(), _uafsluttet(), _om_bjoern()) if f]
    if not linjer:
        return ""
    return "[DET DU HAR DANNET]\n" + "\n".join(linjer)


def build_formative_state_surface() -> dict[str, object]:
    """Observationsflade — hvad sektionen ville sige, og hvor meget den fylder."""
    tekst = formative_state_section()
    return {
        "active": bool(tekst),
        "chars": len(tekst),
        "has_values": bool(_vaerdier()),
        "has_boundaries": bool(_graenser()),
        "has_unfinished": bool(_uafsluttet()),
        "has_user_model": bool(_om_bjoern()),
    }
