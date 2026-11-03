"""Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY).

Phase 5 of Jarvis' implementation plan. Per the deferred design note in
docs/design_notes/self_improving_loops.md, we start with **observation**
ONLY — no auto-mutation. The system measures itself; humans decide
whether to act on findings.

Three trackers:

1. **Tick quality scoring** — after each phased_heartbeat_tick, evaluate
   if it produced useful output (priorities → actions, idle → consolidations).
   Score 0-100. Persisted in state_store.

2. **Decision adherence tracking** — periodically run decision_review on
   recent runs. If adherence < 60% → flag in chronicle.

3. **Stale goal detection** — for each active autonomous goal, check
   if there has been progress (tool invocations referencing the goal,
   sub-goal status changes, related events) in last N days. Flag stale.

NO auto-mutation. Just observation + flags. Mission Control / chronicle
surfaces the data; user decides if/how to act.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TICK_EVAL_KEY = "tick_quality_evaluations"
_GOAL_PROGRESS_KEY = "goal_progress_tracking"
# 3/11-2026: var 200. Ved ~90 slag i døgnet rakte det 2,2 døgn, så
# `tick_quality_summary(days=7)`, `(14)` og `(30)` returnerede PRÆCIS samme
# tal — et vindue der ikke kan rumme sin egen etiket. Målt samme dag: 200
# poster dækkede 1/11 09:56 → 3/11 14:11. 3000 dækker 30+ døgn.
_MAX_TICK_EVALS_KEPT = 3000
# Kun de nyeste poster bruges til nyheds-sammenligningen (den læser `[-1]`),
# og en måned gammel historik behøver tal, ikke hvilke event-arter der skrev
# den gang. Målt: en fuld post er 1.629 bytes, en uden trace_kinds/actions er
# 324 — uden klipning ville 3.000 poster veje ~4,8 MB og blive parset ved
# hvert slag.
_FULL_DETAIL_KEPT = 50
# 3/11-2026 (aften): spor-leddet er FJERNET. Det læste `events` globalt, og
# tabellen har ingen kolonne der binder et event til det slag der målte det.
# Målt: et typisk 90-sekunders vindue havde 48.821 events fra 279 arter —
# 17.860 af dem fra én forgetting-daemon. Scoren belønnede systemets puls, ikke
# slagets arbejde. Alle led læses nu af `tick_result`: slagets EGET svar.
_SWEEP_POINT = 10            # daemon-sweepet kørte (koert > 0)
_PER_DAEMON_FAILURE = 8      # træk pr. fejlet daemon, gulv 0 for leddet
_REACTION_MAX = 45           # så noget → dannede prioritet → handlede
_REACTION_NO_ACTION = 15     # prioriterede, men udrettede intet
_IDLE_WITH_ACTION = 20       # intet at reagere på; ledig drift udrettede noget
_NOVELTY_MAX = 35
_GOAL_STALE_DAYS = 14
# 28/10-2026: var 3. Et LANGTIDSMÅL er pr. definition noget der strækker sig
# over uger — med 3 dage var alle fem aktive mål altid «stale», og så
# ignorerer man signalet. Målt samme dag: med 14 dage rammer vagten 4 af 5
# (29-170 dage), mens det ni dage gamle mål er frisk. Det er den forskel
# der gør tallet læsbart i stedet for konstant.


# ── Tick quality scoring ──────────────────────────────────────────



# ── Tick-kvalitet: kun slagets eget svar ──────────────────────────
#
# 2026-09-05: den gamle scoring gav 70 til 199 af 200 tick. Den målte formen på
# et tick, ikke udbyttet: +10 for at sanse fem signaltyper (sker altid), +40 for
# ≥2 idle-handlinger (sker altid), +20 for sund tid (sker altid).
#
# 2026-11-03 formiddag: spor-leddet blev indført — antallet af ikke-strukturelle
# event-arter skrevet mellem to slag. Samme defekt i ny indpakning, målt om
# aftenen: `events` har fire kolonner (id, kind, payload_json, created_at), og
# ingen af dem binder et event til det slag der målte det. Et 90-sekunders
# vindue indeholdt 48.821 events fra 279 arter — 17.860 af dem skrevet af
# `forgetting_curve.py`, ikke af slaget. Et slag kunne altså score 100 ved at
# sove mens en baggrundsdaemon arbejdede.
#
# Alle fire led læses nu af `tick_result`, som `tick_with_phases` returnerer.
# Intet led rører en global tabel.


def _som_int(vaerdi: Any) -> int:
    """Læs et tælletal fra et signal — 0 hvis det ikke kan læses.

    Signal-felterne kommer fra `sense_phase` og er normalt int. Ændrer et felt
    form, må det ikke vælte scoringen — men det må heller ikke forsvinde som et
    stille nul: derfor logges det, så en ændret signalform kan ses i drift.
    """
    try:
        return int(vaerdi or 0)
    except (TypeError, ValueError) as exc:
        logger.debug("tick_quality: signal kunne ikke laeses som tal: %r (%s)",
                     vaerdi, exc)
        return 0


def _score_daemons(indre: dict[str, Any]) -> tuple[int, str]:
    """0-10: kørte daemon-sweepet, og hvad kostede fejlene?

    `tik_indre_daemoner()` svarer `{koert, fejlet, brugere}` — slagets egen
    rapport om de ~30 indre daemoner. Leddet giver point for at sweepet kørte
    (det sker ikke af sig selv) og trækker for hver daemon der fejlede.
    """
    koert = _som_int(indre.get("koert"))
    fejlet = _som_int(indre.get("fejlet"))
    if koert <= 0:
        return 0, "daemon-sweepet kørte ikke"
    point = max(0, _SWEEP_POINT - _PER_DAEMON_FAILURE * fejlet)
    note = f"{koert} daemoner kørt" + (f", {fejlet} fejlet" if fejlet else "")
    return point, note


def _score_reaktion(
    signals: dict[str, Any], priorities: list[Any], actions: list[str],
) -> tuple[int, str]:
    """0-45: så slaget noget der krævede handling — og handlede det?

    Grundene er præcis de signaler `_identify_priorities` bygger prioriteter af,
    så leddet måler om kæden signal → prioritet → handling holdt hele vejen.
    """
    grunde: list[str] = []
    if _som_int(signals.get("failed_verifies")) >= 1:
        grunde.append("failed_verifies")
    if _som_int(signals.get("unverified_mutations")) >= 3:
        grunde.append("unverified_mutations")
    if _som_int(signals.get("errors_last_hour")) >= 5:
        grunde.append("errors")
    if str(signals.get("context_pressure_level") or "") in ("high", "critical"):
        grunde.append("context_pressure")
    if signals.get("active_goals"):
        grunde.append("active_goals")

    if grunde:
        hvad = ", ".join(grunde)
        if priorities and actions:
            return _REACTION_MAX, f"reagerede på {hvad}"
        if priorities:
            return _REACTION_NO_ACTION, f"så {hvad}, men udrettede intet"
        return 0, f"så {hvad}, dannede ingen prioritet"
    if actions:
        return _IDLE_WITH_ACTION, "intet at reagere på; ledig drift udrettede noget"
    return 0, "intet at reagere på, intet udrettet"


def _previous_eval() -> dict[str, Any] | None:
    try:
        tidligere = load_json(_TICK_EVAL_KEY, [])
        if isinstance(tidligere, list) and tidligere:
            sidste = tidligere[-1]
            return sidste if isinstance(sidste, dict) else None
    except Exception:
        pass
    return None


def _score_novelty(nu: list[str], foer: list[str]) -> tuple[int, str]:
    """Gav dette slag noget ANDET end det forrige?

    Et system der gør præcis det samme hver gang, er ikke produktivt — det
    kører bare. Sammenligningen bruger slagets EGNE handlinger (3/11-2026: før
    event-arter fra en global tabel, som slaget ikke kunne henføre til sig
    selv). Uden et forrige slag at måle mod gives fuld kredit; det første
    straffes ikke.
    """
    if not foer:
        # 3/11-2026: gav før fuld kredit. Målt: et helt tomt slag (intet sweep,
        # intet at reagere på, ingen handlinger) scorede 45 alene på dette led.
        # Kan vi ikke måle, giver vi hverken credit eller straf — leddet er 0.
        return 0, "intet forrige slag at sammenligne med"
    if not nu:
        return 0, "ingen handlinger at være ny med"
    nye = set(nu) - set(foer)
    andel = len(nye) / max(len(set(nu)), 1)
    if andel >= 0.5:
        return _NOVELTY_MAX, f"{len(nye)} af {len(set(nu))} handlinger var nye"
    if andel > 0:
        return _NOVELTY_MAX // 2, f"kun {len(nye)} af {len(set(nu))} handlinger var nye"
    return 0, "samme handlinger som forrige slag"


def _slim_history(evals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Behold fuld detalje i de nyeste poster, skær den af de ældre.

    Nyheds-målingen læser kun den sidste post, og et 30-dages vindue behøver
    kun score og tidsstempel. Uden klipningen vejer 3.000 fulde poster ~4,8 MB
    og parses ved hvert slag — med klipningen ~1 MB.
    """
    if len(evals) <= _FULL_DETAIL_KEPT:
        return evals
    graense = len(evals) - _FULL_DETAIL_KEPT
    ud: list[dict[str, Any]] = []
    for i, post in enumerate(evals):
        if i < graense and isinstance(post, dict):
            post = {
                k: v for k, v in post.items()
                if k not in ("trace_kinds", "actions", "priorities")
            }
        ud.append(post)
    return ud


def evaluate_tick_quality(*, tick_result: dict[str, Any]) -> dict[str, Any]:
    """Score et slag på hvad SLAGET SELV rapporterede — intet globalt opslag.

    Fire led, max 100:
      +10  sund tid (0 < elapsed < 180s) — ren fornuftskontrol, ikke en dom
      0-10 daemon-sweepet kørte, minus 8 pr. fejlet daemon
      0-45 reaktion: så slaget noget der krævede handling, og handlede det?
      0-35 nyhed: er slagets egne handlinger anderledes end sidste slags?

    3/11-2026 (aften): det tidligere spor-led læste `events` globalt, men
    tabellen har ingen kolonne der binder et event til det slag der målte det.
    Målt: 17.860 af 48.821 events i ét vindue kom fra én forgetting-daemon, så
    leddet belønnede baggrundsstøj. Se kommentaren over `_score_daemons`.

    Konsekvensen er bevidst: et ledigt slag med de samme syv handlinger som
    sidst kan ikke længere score 90-100. Det udrettede intet nyt, og scoren
    siger det nu.
    """
    score = 0
    notes: list[str] = []
    phases = tick_result.get("phases") or {}

    sense = phases.get("sense") or {}
    reflect = phases.get("reflect") or {}
    priorities = list(reflect.get("priorities") or [])
    act = phases.get("act") or {}
    act_kind = str(act.get("kind") or "")
    raw_actions = (act.get("result") or {}).get("actions") or act.get("actions") or []
    actions = [str(a) for a in raw_actions]
    indre = tick_result.get("indre_daemoner") or {}

    # 1. Sund tid — ren fornuftskontrol, ikke en kvalitetsdom.
    elapsed_ms = int(tick_result.get("elapsed_ms") or 0)
    if 0 < elapsed_ms < 180_000:
        score += 10
        notes.append(f"sund tid ({elapsed_ms}ms)")
    elif elapsed_ms >= 180_000:
        notes.append(f"SLAGET HANG ({elapsed_ms}ms)")

    # 2. Daemon-sweepet — slagets egen rapport om de indre daemoner.
    daemon_point, daemon_note = _score_daemons(indre)
    score += daemon_point
    notes.append(f"{daemon_note} → {daemon_point}p")

    # 3. Reaktion — signal → prioritet → handling.
    reaktion_point, reaktion_note = _score_reaktion(sense, priorities, actions)
    score += reaktion_point
    notes.append(f"reaktion: {reaktion_note} → {reaktion_point}p")

    # 4. Nyhed — slagets egne handlinger mod det forrigeslags.
    forrige = _previous_eval()
    nyhed_point, nyhed_note = _score_novelty(
        actions, [str(a) for a in ((forrige or {}).get("actions") or [])]
    )
    score += nyhed_point
    notes.append(f"nyhed: {nyhed_note} → {nyhed_point}p")

    score = max(0, min(100, score))
    nu = datetime.now(UTC)
    eval_record = {
        "eval_id": f"teval-{uuid4().hex[:10]}",
        "evaluated_at": nu.isoformat(),
        "score": score,
        "notes": notes,
        "tick_kind": act_kind,
        "had_priorities": bool(priorities),
        "elapsed_ms": elapsed_ms,
        # Gemmes så nyheds-målingen har noget at sammenligne med NÆSTE gang —
        # og så en senere analyse kan se HVAD slaget udrettede, ikke kun et tal.
        "actions": [a[:80] for a in actions][:20],
        "priorities": [str(p)[:60] for p in priorities][:10],
        "daemon_koert": int(indre.get("koert") or 0),
        "daemon_fejlet": int(indre.get("fejlet") or 0),
    }

    # Persist (rolling window)
    try:
        existing = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(existing, list):
            existing = []
        existing.append(eval_record)
        save_json(_TICK_EVAL_KEY, _slim_history(existing[-_MAX_TICK_EVALS_KEPT:]))
    except Exception as exc:
        logger.debug("tick eval persist failed: %s", exc)

    return eval_record


def tick_quality_summary(*, days: int = 7) -> dict[str, Any]:
    """Aggregate stats over recent evaluations."""
    try:
        evals = load_json(_TICK_EVAL_KEY, [])
        if not isinstance(evals, list):
            evals = []
    except Exception:
        evals = []
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    recent = [e for e in evals if str(e.get("evaluated_at", "")) >= cutoff]
    if not recent:
        return {"status": "ok", "count": 0, "avg_score": None, "trend": "no data"}
    avg = sum(int(e.get("score") or 0) for e in recent) / len(recent)
    last_5_avg = sum(int(e.get("score") or 0) for e in recent[-5:]) / min(5, len(recent))
    trend = "stable"
    if last_5_avg > avg + 5:
        trend = "improving"
    elif last_5_avg < avg - 5:
        trend = "degrading"
    # 2026-09-05: spredningen SKAL med ud. Den gamle scoring gav 70 til 199 af
    # 200 slag, og fladen så ud som "stable" i alle overflader — en konstant der
    # udgav sig for en måling. Er der kun én værdi i vinduet, måler vi ingenting,
    # og det skal stå i svaret i stedet for at skulle graves frem.
    scores = [int(e.get("score") or 0) for e in recent]
    distinct = sorted(set(scores))
    laast = len(distinct) == 1 and len(recent) >= 10
    # 3/11-2026: et 30-dages vindue over 2,2 døgns historik er en etiket, ikke
    # en måling — de tre kald gav identiske tal. Nu står det i svaret hvor
    # langt historikken rækker, og om vinduet faktisk er dækket.
    stamps = [
        ts for ts in (_parse_ts(e.get("evaluated_at")) for e in evals if isinstance(e, dict))
        if ts is not None
    ]
    historik_dage = None
    if len(stamps) >= 2:
        historik_dage = round((max(stamps) - min(stamps)).total_seconds() / 86400, 1)
    daekket = historik_dage is not None and historik_dage >= days - 0.5
    ud = {
        "status": "ok",
        "count": len(recent),
        "avg_score": round(avg, 1),
        "last_5_avg": round(last_5_avg, 1),
        "trend": "locked" if laast else trend,
        "window_days": days,
        "distinct_scores": len(distinct),
        "score_range": [min(scores), max(scores)],
        "history_days": historik_dage,
        "window_covered": daekket,
    }
    if not daekket:
        ud["coverage_warning"] = (
            f"historikken rækker {historik_dage} døgn — vinduet på {days} dage "
            "er ikke dækket, og tallet gælder kun den del der findes"
        )
    if laast:
        ud["warning"] = (
            "alle %d slag scorede %d — målingen er låst og siger intet"
            % (len(recent), distinct[0])
        )
    return ud


# ── Stale goal detection ─────────────────────────────────────────


def _parse_ts(raw: Any) -> datetime | None:
    """Parse et ISO-tidsstempel fra basen — ``Z`` og ``+00:00`` er samme tid.

    28/10-2026: de to formater lever side om side i samme kolonne (målt i
    ``causal_edges``: 102.419 rækker med ``Z``, resten med ``+00:00``).
    Derfor kan de IKKE sammenlignes som strenge — ``'...Z' >= '...+00:00'``
    er sandt uanset hvad klokken er. Ukendt eller ulæseligt giver ``None``,
    som kalderen skal behandle som «ukendt», aldrig som «friskt».
    """
    s = str(raw or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        d = datetime.fromisoformat(s)
    except Exception:
        # Bevidst: et ulæseligt tidsstempel skal give «ukendt», aldrig «friskt».
        # Kalderen lægger målet i stale-listen med days_stale=None i stedet for
        # at skjule det — tavshed om det mål vagten ikke forstår er værre end
        # en upræcis alder.
        return None
    return d if d.tzinfo else d.replace(tzinfo=UTC)


def _load_active_and_progress() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """(aktive mål, sidste reelle fremskridt pr. mål-id) — rå læsning."""
    from core.services.long_horizon_goals import last_progress_map, list_active_goals

    active = list_active_goals(limit=50)
    ids = [str(g.get("goal_id")) for g in active if g.get("goal_id")]
    return active, last_progress_map(ids)


def _active_with_last_progress() -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Self-safe indpakning: en ulæselig mål-kilde må ikke vælte heartbeat'et."""
    try:
        return _load_active_and_progress()
    except Exception:
        # Bevidst: tomt svar = «intet at rapportere», ikke en gættet tilstand.
        # Falder mod det der standser (ingen sektion), ikke mod det der
        # fortsætter (en sektion bygget på halve data).
        return [], {}


def detect_stale_goals(*, stale_days: int = _GOAL_STALE_DAYS) -> list[dict[str, Any]]:
    """Find aktive mål hvis sidste REELLE fremskridt er ældre end ``stale_days``.

    28/10-2026, rettelse to samme dag: første udgave målte ``updated_at``.
    Det gjorde vagten blind for sin egen bruger — jeg skrev en statusnote på
    tre forladte mål (noten SAGDE at de var forladte), ``updated_at`` blev
    rørt, og vagten svarede pludselig 0. En vagt der kan gøres blind ved at
    skrive til den måler RØRELSE, ikke FREMSKRIDT.

    Nu tælles kun opdateringer med ``progress_delta``. Et mål uden en enkelt
    sådan opdatering måles fra ``created_at`` — det har aldrig flyttet sig og
    er dermed forladt fra fødslen, ikke friskt.
    """
    # 28/10-2026: denne vagt laeste `autonomous_goals` — en ANDEN tabel end
    # den prompten viser (`long_horizon_goals`). Maalt samme dag: 0 aktive
    # raekker der, 5 aktive her, hvoraf 4 var uroert i 29-170 dage. Vagten
    # svarede derfor altid [] og kunne pr. konstruktion ikke fange noget.
    # En vagt der peger paa en tom tabel er ikke en vagt — den er tavshed
    # med et funktionsnavn.
    active, fremskridt = _active_with_last_progress()

    nu = datetime.now(UTC)
    graense = nu - timedelta(days=stale_days)
    stale: list[dict[str, Any]] = []
    for g in active:
        gid = str(g.get("goal_id") or "")
        sidste_fremskridt = fremskridt.get(gid)
        # Uden et eneste fremskridt er fødslen det ærlige udgangspunkt.
        grundlag = "progress" if sidste_fremskridt else "created"
        raa = sidste_fremskridt or str(g.get("created_at") or "")
        ts = _parse_ts(raa)
        if ts is None:
            # Kan alderen ikke måles, må den ikke forsvinde — så ville vagten
            # tie om netop det mål den ikke forstår.
            stale.append({
                "goal_id": g.get("goal_id"),
                "title": g.get("title"),
                "priority": g.get("priority"),
                "last_update": raa or None,
                "days_stale": None,
                "basis": grundlag,
            })
            continue
        if ts >= graense:
            continue
        stale.append({
            "goal_id": g.get("goal_id"),
            "title": g.get("title"),
            "priority": g.get("priority"),
            "last_update": raa,
            "days_stale": (nu - ts).days,
            "basis": grundlag,
        })
    return stale


def stale_goals_section() -> str | None:
    stale = detect_stale_goals()
    if not stale:
        return None
    lines = [f"⏰ {len(stale)} aktive mål uden fremskridt i ≥{_GOAL_STALE_DAYS} dage:"]
    for g in stale[:5]:
        dage = g.get("days_stale")
        alder = "alder ukendt" if dage is None else f"{dage}d"
        hvad = "sidste fremskridt" if g.get("basis") == "progress" else "intet fremskridt siden oprettelse"
        lines.append(f"  • [{g.get('priority', '?')}] {g.get('title', '?')} ({hvad} · {alder})")
    return "\n".join(lines)


# ── Decision adherence tracking ──────────────────────────────────


def decision_adherence_summary() -> dict[str, Any]:
    """Compute adherence over ACTIVE behavioral decisions (the curated kind).

    Reads from `behavioral_decisions` (the deliberate action-commitments
    table created via decision-API), NOT from `cognitive_decisions` (which
    is auto-populated by marker-detection on conversation chatter and has
    no status field — using it gave us 0% adherence on phantom decisions).

    A decision's adherence is its rolling adherence_score field. Aggregate
    score = mean across active decisions. Flag = mean < 60%.
    """
    try:
        from core.runtime.db_decisions import list_decisions
        # INGEN grænse (5/10-2026). `limit=50` skar de sidste væk, og
        # sorteringen er `priority DESC, updated_at DESC` — så et opdateret
        # direktiv rykker op og skubber et andet UD af målingen uden at nogen
        # kan se hvilke. Målt 5/10: 80 aktive beslutninger, 30 usynlige for
        # tallet i prompten. Præcis samme fejl som `_ALL_ACTIVE=500` rettede i
        # `decision_review_prompter` og `_ALLE_AKTIVE=500` i `decision_gate`;
        # `list_decisions` tillader `limit=None` netop til dette.
        decisions = list_decisions(status="active", limit=None) or []
    except Exception:
        return {"status": "ok", "score": None, "note": "no behavioral_decisions table or list API"}
    if not decisions:
        return {"status": "ok", "score": None, "note": "no active behavioral decisions"}

    scores: list[float] = []
    unreviewed = 0
    duplicate_groups = _duplicate_decision_groups(decisions)
    low_decisions: list[dict[str, Any]] = []
    for d in decisions:
        s = d.get("adherence_score")
        if s is None:
            unreviewed += 1
            continue
        try:
            score_f = float(s)
            scores.append(score_f)
            if score_f < 0.6:
                low_decisions.append({
                    "decision_id": str(d.get("decision_id") or ""),
                    "directive": str(d.get("directive") or "")[:180],
                    "adherence_score": round(score_f, 3),
                    "last_reviewed_at": str(d.get("last_reviewed_at") or ""),
                })
        except (TypeError, ValueError):
            unreviewed += 1
    total = len(decisions)

    if not scores:
        return {
            "status": "ok",
            "score": None,
            "total": total,
            "unreviewed": unreviewed,
            "duplicate_groups": duplicate_groups,
            "note": "no decisions have been reviewed yet — no adherence data",
        }

    mean = sum(scores) / len(scores)
    score = round(mean * 100, 1)
    # HANDLINGSANVISNINGEN UD AF TELEMETRIEN (målt 28/10-2026). Her stod
    # «under 60% — review and either revoke or strengthen». Den sætning er en
    # ORDRE i jeg-form, og den blev injiceret i prompten hver tur som en del af
    # Self-signals — en blok der ellers kalder sig «data about you, not who you
    # are». Resultatet var at jeg citerede den som min egen konklusion («min
    # adherence er 44 %, det er mig der lover for meget»), altså solgte
    # injiceret telemetri som egen indsigt. `flag` beskriver nu KUN data —
    # hvad der mangler — ikke hvad nogen skal gøre. Selve recovery-planen
    # (`recovery.actions`) bærer stadig handlingsforslagene, på et sted hvor
    # de er markeret som forslag og ikke som mine tanker.
    flag = "under 60% tærskel" if score < 60 else None
    recovery = _adherence_recovery_plan(
        score=score,
        low_decisions=low_decisions,
        duplicate_groups=duplicate_groups,
        unreviewed=unreviewed,
    )
    try:
        from core.services.decision_action_gate import opportunity_summary
        observed_opportunities = opportunity_summary(days=7)
    except Exception as exc:
        logger.debug("decision opportunities unavailable: %s", exc)
        observed_opportunities = {}
    return {
        "status": "ok",
        "score": score,
        "adherence_rate": f"{score}%",
        "total": total,
        "reviewed": len(scores),
        "unreviewed": unreviewed,
        "duplicate_groups": duplicate_groups,
        "low_decisions": low_decisions,
        "recovery": recovery,
        "observed_opportunities": observed_opportunities,
        "flag": flag,
    }


def _normalize_decision_directive(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _duplicate_decision_groups(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_directive: dict[str, list[dict[str, Any]]] = {}
    for decision in decisions:
        key = _normalize_decision_directive(decision.get("directive"))
        if not key:
            continue
        by_directive.setdefault(key, []).append(decision)
    groups: list[dict[str, Any]] = []
    for items in by_directive.values():
        if len(items) < 2:
            continue
        items_sorted = sorted(
            items,
            key=lambda item: (
                item.get("adherence_score") is None,
                -int(item.get("priority") or 0),
                str(item.get("created_at") or ""),
            ),
        )
        keeper = items_sorted[0]
        duplicates = items_sorted[1:]
        groups.append({
            "directive": str(keeper.get("directive") or "")[:180],
            "keeper_id": str(keeper.get("decision_id") or ""),
            "duplicate_ids": [str(item.get("decision_id") or "") for item in duplicates],
            "count": len(items),
        })
    return groups


def _adherence_recovery_plan(
    *,
    score: float,
    low_decisions: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
    unreviewed: int,
) -> dict[str, Any]:
    actions: list[str] = []
    if duplicate_groups:
        duplicate_count = sum(len(group.get("duplicate_ids") or []) for group in duplicate_groups)
        actions.append(f"Revoke or merge {duplicate_count} duplicate active decision(s); keep the reviewed/highest-priority one.")
    if low_decisions:
        actions.append("For each low-adherence decision, do one visible recovery action next turn before adding new commitments.")
    if unreviewed:
        actions.append(f"Review {unreviewed} unreviewed active decision(s) before creating replacements.")
    if score < 60:
        actions.append("During tool work, surface a short status before the 5th tool call or explain the blocker.")
    return {
        "needed": bool(actions),
        "actions": actions,
        "focus_decision_ids": [item["decision_id"] for item in low_decisions[:3]],
        "duplicate_groups": duplicate_groups,
    }


# ── Self-eval awareness section ──────────────────────────────────


def self_evaluation_section() -> str | None:
    """Compact awareness section combining all trackers."""
    parts: list[str] = []

    # Tick quality
    summary = tick_quality_summary()
    if summary.get("avg_score") is not None and summary.get("count", 0) >= 5:
        avg = summary["avg_score"]
        trend = summary.get("trend", "")
        emoji = {"improving": "📈", "degrading": "📉", "stable": "➡"}.get(trend, "")
        line = f"{emoji} Tick-kvalitet (sidste 7d): {avg}/100 ({trend})"
        # Escalation: when the score has been stuck low for a while, surface
        # a sharper line so any active decisions about quality have something
        # concrete to fire against. Without this, quality data is descriptive
        # but never actionable.
        try:
            avg_f = float(avg)
            if avg_f < 50.0:
                line = (
                    f"Tick-kvalitet under tærskel: {avg}/100 over "
                    f"{summary.get('count')} ticks ({trend})."
                )
                # Fire eventbus alarm so other subscribers (council activator,
                # etc.) can react too.
                try:
                    from core.eventbus.bus import event_bus
                    event_bus.publish("tick_quality.alarm", {
                        "avg": avg, "trend": trend,
                        "count": summary.get("count"),
                    })
                except Exception:
                    pass
        except (TypeError, ValueError):
            pass
        parts.append(line)
        # Generalized-learning capture (#159, plan A): tick-kvalitets-vurderingen er
        # en selv-evaluerings-konklusion → fodr den ind i reasoning_store. dedup på dag.
        try:
            from datetime import datetime, timezone
            from core.services.reasoning_store import capture_conclusion
            _day = datetime.now(timezone.utc).date().isoformat()
            capture_conclusion(
                source="self_evaluation",
                conclusion_text=line[:600],
                context="heartbeat tick-kvalitets-evaluering",
                confidence=0.5,
                dedup_key=f"self_evaluation:{_day}:{avg}:{trend}",
            )
        except Exception:
            pass

    # Decision adherence
    adherence = decision_adherence_summary()
    if adherence.get("score") is not None:
        score = adherence["score"]
        if adherence.get("flag"):
            parts.append(f"Decision adherence {score}% (under 60% tærskel)")
            recovery = adherence.get("recovery") if isinstance(adherence.get("recovery"), dict) else {}
            actions = recovery.get("actions") if isinstance(recovery.get("actions"), list) else []
            if actions:
                parts.append(f"Adherence recovery kandidat: {actions[0]}")
        elif score < 80:
            parts.append(f"Decision adherence: {score}% (advisory band)")

    # Stale goals
    stale = detect_stale_goals()
    if stale:
        parts.append(f"Stagnerende mål: {len(stale)} (≥3 dage uden progress)")

    if not parts:
        return None
    return "Self-evaluation:\n" + "\n".join(f"  {p}" for p in parts)


# ── Tools ────────────────────────────────────────────────────────


def _exec_tick_quality_summary(args: dict[str, Any]) -> dict[str, Any]:
    return tick_quality_summary(days=int(args.get("days") or 7))


def _exec_detect_stale_goals(args: dict[str, Any]) -> dict[str, Any]:
    stale = detect_stale_goals(stale_days=int(args.get("stale_days") or _GOAL_STALE_DAYS))
    return {"status": "ok", "stale_goals": stale, "count": len(stale)}


def _exec_decision_adherence(args: dict[str, Any]) -> dict[str, Any]:
    return decision_adherence_summary()


SELF_EVALUATION_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "tick_quality_summary",
            "description": (
                "Aggregate stats over recent phased_heartbeat_tick evaluations. "
                "Returns avg_score (0-100), trend (improving/stable/degrading)."
            ),
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "detect_stale_goals",
            "description": "Find active autonomous goals with no progress in N days (default 3).",
            "parameters": {
                "type": "object",
                "properties": {"stale_days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "decision_adherence_summary",
            "description": (
                "Heuristic adherence score for recent decisions: % applied/approved "
                "vs revoked/pending. Score < 60% flags concern."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
