"""Internal-opposition signal tracking — migrated onto signal_tracking_framework.

The public surface is unchanged (byte-identical behaviour): the three functions
below delegate the shared lifecycle scaffolding (persist / refresh-to-stale /
surface bucketing / event publishing) to :mod:`signal_tracking_framework`, while
the internal-opposition-specific cross-layer candidate derivation and domain-key
mapping stay here — that is the part unique to internal opposition.

This is a plain ``{active,softening}`` S-family multi-candidate variant (no
policy-layer surface, no ``recent_history``). Its ``_build_candidate`` uses the
same ``high if >=3 source items else medium`` confidence rule ``make_candidate``
defaults to, so only its ``runtime-derived-support`` ``source_kind`` is passed
explicitly. The display token stays "internal opposition" (a space, not the
hyphenated slug) via ``track_summary_fn``.
"""
from __future__ import annotations

from core.services import signal_tracking_framework as _stf
from core.services.signal_tracking_framework import SignalTrackingSpec, make_candidate
from core.services.open_loop_signal_tracking import (
    build_runtime_open_loop_signal_surface,
)
from core.runtime.db import (
    list_runtime_development_focuses,
    list_runtime_goal_signals,
    list_runtime_internal_opposition_signals,
    list_runtime_reflective_critics,
    list_runtime_reflection_signals,
    list_runtime_self_model_signals,
    list_runtime_temporal_recurrence_signals,
    list_runtime_world_model_signals,
    supersede_runtime_internal_opposition_signals_for_domain,
    update_runtime_internal_opposition_signal_status,
    upsert_runtime_internal_opposition_signal,
)

_STALE_AFTER_DAYS = 14


# ── public surface (thin delegates; signatures unchanged) ─────────────────────
def track_runtime_internal_opposition_signals_for_visible_turn(
    *,
    session_id: str | None,
    run_id: str,
) -> dict[str, object]:
    return _stf.track_for_visible_turn(_SPEC, session_id=session_id, run_id=run_id)


def refresh_runtime_internal_opposition_signal_statuses() -> dict[str, int]:
    return _stf.refresh_statuses(_SPEC)


def build_runtime_internal_opposition_signal_surface(*, limit: int = 8) -> dict[str, object]:
    return _stf.build_surface(_SPEC, limit=limit)


#: Hvor mange raekker der hentes pr. lag. Maalt 4/11-2026: med 18 kunne
#: lagene naesten ikke moedes (nyeste-18 focus ∩ nyeste-18 critic = 0), fordi
#: hvert lag har sin egen produktionsrytme. Vinduet skal vaere stoerre end
#: antallet af koersler der baerer 2+ lag.
_WINDOW = 400


def _run_domain(item: dict[str, object], key_fn) -> str:
    """Domaenet er KOERSLEN, ikke et semantisk emne.

    Maalt 4/11-2026: lagene taler ikke samme spoerg. `focus` er sin egen
    saetning, `goal` sin egen slug, `critic` en type — saa noegle-parsing gav
    `critic ∩ alt = 0`. Koerslen er den ene dimension ALLE lag baerer, og det
    er ogsaa den signalet handler om: «i DENNE tur pegede to lag modsat».

    Graensen skal siges hoejt: dette er et TIDSLIGT domaene, ikke et semantisk.
    Det fanger at to ting skete i samme tur — ikke at de handler om det samme.
    Det er den korrekte betydning for intern opposition; for spoergsmaalet
    «samme emne over tid» (open-loop, recurrence) er domaenet stadig emnet.

    Uden anker falder vi tilbage til noegle-udtraekket, saa gamle raekker uden
    `run_id` opfoerer sig som foer.
    """
    anchor = str(item.get("run_id") or "").strip()
    if anchor:
        return anchor
    return key_fn(str(item.get("canonical_key") or ""))


# ── internal-opposition-specific cross-layer candidate derivation (unique) ─────
def _extract_internal_opposition_candidates(*_args, **_kwargs) -> list[dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}

    for focus in list_runtime_development_focuses(limit=_WINDOW):
        if str(focus.get("status") or "") != "active":
            continue
        domain_key = _run_domain(focus, _focus_domain_key)
        if domain_key:
            snapshots.setdefault(domain_key, {})["active_focus"] = focus

    for goal in list_runtime_goal_signals(limit=_WINDOW):
        status = str(goal.get("status") or "")
        if status not in {"active", "blocked"}:
            continue
        domain_key = _run_domain(goal, _goal_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "blocked":
            bucket["blocked_goal"] = goal
        else:
            bucket["active_goal"] = goal

    for critic in list_runtime_reflective_critics(limit=_WINDOW):
        status = str(critic.get("status") or "")
        if status not in {"active", "resolved"}:
            continue
        domain_key = _run_domain(critic, _critic_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_critic"] = critic
        else:
            bucket["resolved_critic"] = critic

    for signal in list_runtime_self_model_signals(limit=_WINDOW):
        status = str(signal.get("status") or "")
        if status not in {"active", "uncertain"}:
            continue
        domain_key = _run_domain(signal, _self_model_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_self_model"] = signal
        else:
            bucket["uncertain_self_model"] = signal

    for signal in list_runtime_reflection_signals(limit=_WINDOW):
        status = str(signal.get("status") or "")
        if status not in {"active", "integrating", "settled"}:
            continue
        domain_key = _run_domain(signal, _reflection_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "settled":
            bucket["settled_reflection"] = signal
        else:
            bucket["live_reflection"] = signal

    for signal in list_runtime_temporal_recurrence_signals(limit=_WINDOW):
        status = str(signal.get("status") or "")
        if status not in {"active", "softening"}:
            continue
        domain_key = _run_domain(signal, _temporal_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "active":
            bucket["active_recurrence"] = signal
        else:
            bucket["softening_recurrence"] = signal

    for item in build_runtime_open_loop_signal_surface(limit=_WINDOW).get("items", []):
        status = str(item.get("status") or "")
        if status not in {"open", "softening"}:
            continue
        domain_key = _run_domain(item, _open_loop_domain_key)
        if not domain_key:
            continue
        bucket = snapshots.setdefault(domain_key, {})
        if status == "open":
            bucket["open_loop"] = item
        else:
            bucket["softening_loop"] = item

    world_uncertain_signals = [
        item
        for item in list_runtime_world_model_signals(limit=_WINDOW)
        if str(item.get("status") or "") == "uncertain"
    ]
    active_goal_count = len([item for item in list_runtime_goal_signals(limit=_WINDOW) if str(item.get("status") or "") in {"active", "blocked"}])
    open_loop_surface = build_runtime_open_loop_signal_surface(limit=_WINDOW)

    candidates: list[dict[str, object]] = []
    for domain_key, snapshot in snapshots.items():
        active_focus = snapshot.get("active_focus")
        active_goal = snapshot.get("active_goal")
        blocked_goal = snapshot.get("blocked_goal")
        active_critic = snapshot.get("active_critic")
        resolved_critic = snapshot.get("resolved_critic")
        active_self_model = snapshot.get("active_self_model")
        uncertain_self_model = snapshot.get("uncertain_self_model")
        live_reflection = snapshot.get("live_reflection")
        settled_reflection = snapshot.get("settled_reflection")
        active_recurrence = snapshot.get("active_recurrence")
        softening_recurrence = snapshot.get("softening_recurrence")
        open_loop = snapshot.get("open_loop")
        softening_loop = snapshot.get("softening_loop")
        title_suffix = _domain_title(_snapshot_label(snapshot, domain_key))

        if (open_loop and str(open_loop.get("signal_type") or "") == "persistent-open-loop" and active_critic and (active_focus or active_goal or blocked_goal)) or (
            active_critic and active_recurrence and (active_focus or active_goal or blocked_goal)
        ):
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-direction",
                    status="active",
                    title=f"Challenge direction: {title_suffix}",
                    summary=f"This bounded direction around {title_suffix.lower()} now looks like it should face internal challenge rather than simple continuation.",
                    rationale="Persistent unresolved pressure is still pushing against an active focus or goal in the same domain.",
                    status_reason="Active critic pressure and recurring/open-loop evidence make this direction a candidate for bounded internal opposition.",
                    source_items=[active_focus, active_goal, blocked_goal, active_critic, active_recurrence, open_loop],
                )
            )
            continue

        # Maalt 4/11-2026: critic ∩ self_model = 0 koersler, focus ∩ critic = 1.
        # De tre lag produceres i hver sin rytme, saa et krav om alle tre var et
        # krav om at to ure slaar samtidig. Fokus + selv-model ER to lag i samme
        # koersel og er nok til at baere en kalibrerings-indsigelse; critic,
        # open-loop og recurrence styrker den naar de findes.
        if (active_focus or active_goal) and (active_self_model or uncertain_self_model):
            lag = _lag_pair_label(snapshot)
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-calibration",
                    status="active",
                    title=f"Challenge calibration: {lag}",
                    summary=f"Kalibrering i denne kørsel: {lag}.",
                    rationale="To lag sameksisterer i samme kørsel. Om de modsiger hinanden er ikke afgjort — domænet er tidsligt, ikke semantisk.",
                    status_reason="Begge lag er til stede i samme kørsel; en eventuel modsætning skal læses ud af deres indhold.",
                    source_items=[active_focus, active_goal, active_self_model, uncertain_self_model, active_critic, open_loop, active_recurrence],
                )
            )
            continue

        if (softening_loop or softening_recurrence or resolved_critic) and (active_self_model or uncertain_self_model or live_reflection) and not active_critic and not blocked_goal:
            lag = _lag_pair_label(snapshot)
            candidates.append(
                _build_candidate(
                    domain_key=domain_key,
                    signal_type="challenge-calibration",
                    status="softening",
                    title=f"Softening challenge: {lag}",
                    summary=f"Kalibrering i denne kørsel: {lag}.",
                    rationale="To lag sameksisterer i samme kørsel, men presset er aftagende. Om de modsiger hinanden er ikke afgjort.",
                    status_reason="Begge lag er til stede, men den skarpe kritiker/open-loop-pres er væk.",
                    source_items=[active_focus, active_goal, active_self_model, uncertain_self_model, live_reflection, softening_loop, softening_recurrence, resolved_critic, settled_reflection],
                )
            )

    if world_uncertain_signals and (active_goal_count > 0 or open_loop_surface.get("active")):
        item = world_uncertain_signals[0]
        title_suffix = str(item.get("title") or "Current world view").replace("Current ", "")
        status = "active" if open_loop_surface.get("summary", {}).get("open_count") else "softening"
        candidates.append(
            _build_candidate(
                domain_key=f"world:{_world_domain_key(str(item.get('canonical_key') or ''))}",
                signal_type="challenge-world-view",
                status=status,
                title=f"Challenge world view: {title_suffix}",
                summary="A bounded situational assumption now looks uncertain enough that Jarvis should visibly keep it challengeable.",
                rationale="An uncertain world-model thread is still present while active direction or unresolved loops remain live elsewhere in runtime truth.",
                status_reason="Situational understanding remains bounded and challengeable while work direction is still live.",
                source_items=[item],
            )
        )

    return candidates[:4]


def _build_candidate(
    *,
    domain_key: str,
    signal_type: str,
    status: str,
    title: str,
    summary: str,
    rationale: str,
    status_reason: str,
    source_items: list[dict[str, object] | None],
) -> dict[str, object]:
    # canonical_key = "internal-opposition:{signal_type}:{domain_key}"; confidence
    # high when >=3 source layers else medium (make_candidate's default) — matches
    # the original exactly. source_kind is the file's own "runtime-derived-support".
    return make_candidate(
        _SPEC,
        signal_type=signal_type,
        discriminator=signal_type,
        key=domain_key,
        status=status,
        title=title,
        summary=summary,
        rationale=rationale,
        status_reason=status_reason,
        source_items=source_items,
        source_kind="runtime-derived-support",
        group_value=domain_key,
    )


def _internal_opposition_track_summary(items: list[dict[str, object]], message: str) -> str:
    return (
        f"Tracked {len(items)} bounded internal opposition signals."
        if items
        else "No bounded internal opposition signal warranted tracking."
    )


# ── spec: standard S-family knobs + _for_domain supersede ──────────────────────
_SPEC = SignalTrackingSpec(
    name="internal-opposition",
    slug="internal-opposition",
    signal_id_prefix="opposition",
    event_prefix="internal_opposition_signal",
    default_signal_type="internal-opposition",
    list_fn=list_runtime_internal_opposition_signals,
    upsert_fn=upsert_runtime_internal_opposition_signal,
    update_status_fn=update_runtime_internal_opposition_signal_status,
    supersede_fn=supersede_runtime_internal_opposition_signals_for_domain,
    supersede_group_field="domain_key",
    supersede_group_kw="domain_key",
    extract_fn=_extract_internal_opposition_candidates,
    stale_after_days=_STALE_AFTER_DAYS,
    refreshable_statuses=frozenset({"active", "softening"}),
    stale_status_reason="Marked stale after bounded internal-opposition inactivity window.",
    surface_status_order=("active", "softening", "stale", "superseded"),
    surface_active_statuses=frozenset({"active", "softening"}),
    empty_current_label="No active internal opposition signal",
    omit_recent_history=True,
    stale_payload_extra=("status_reason",),
    track_summary_fn=_internal_opposition_track_summary,
)


# ── internal-opposition-specific domain-key mapping + labels (unique) ──────────
def _focus_domain_key(canonical_key: str) -> str:
    # 4/11-2026: domænet er det TREDJE segment, ikke det sidste. Begge fokus-
    # formater har et to-segments præfiks (``focus:bearing:`` /
    # ``development-focus:runtime:``), og det gamle format kan bære en undertype
    # efter domænet: ``development-focus:runtime:visible-work:reinforce-retain``
    # → ``visible-work``. Sidste segment gav ``reinforce-retain`` og brød
    # open-loop-kontrakten (målt i test_visible_runs_open_loop_materialization).
    parts = [part.strip() for part in str(canonical_key or "").split(":") if part.strip()]
    return parts[2] if len(parts) >= 3 else ""


def _goal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 2 else ""


def _critic_domain_key(canonical_key: str) -> str:
    # Domænet er det FEMTE segment: to for ``reflective-critic:mismatch:`` plus
    # to for fokus-nøglens eget præfiks. Type-nøgler som ``critic:user_correction``
    # bærer intet domæne og skal fortsat give tomt.
    parts = [part.strip() for part in str(canonical_key or "").split(":") if part.strip()]
    return parts[4] if len(parts) >= 5 else ""


def _self_model_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _reflection_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _temporal_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _open_loop_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else ""


def _world_domain_key(canonical_key: str) -> str:
    parts = canonical_key.split(":")
    return parts[-1] if len(parts) >= 3 else "world-view"


def _snapshot_label(snapshot: dict[str, object], domain_key: str) -> str:
    """Et læsbart emne til titlen — run-id'et er domænet, ikke en titel.

    Domænet er kørslen, men «Visible 329b63ed» siger intet. Vi bruger den
    titel laget selv bærer, og falder tilbage til domænet.
    """
    for felt in ("active_focus", "active_goal", "blocked_goal", "active_self_model", "active_critic"):
        item = snapshot.get(felt)
        if isinstance(item, dict):
            text = str(item.get("title") or "").strip()
            if text:
                return text[:80]
    return domain_key


def _domain_title(domain_key: str) -> str:
    text = str(domain_key or "").replace("world:", "").replace("-", " ").strip()
    return text[:1].upper() + text[1:] if text else "Internal challenge"


def _lag_pair_label(snapshot: dict[str, object]) -> str:
    """Begge lags tekst i ÉN linje — fordi det kun er titlen der når prompten.

    Målt 4/11-2026: ``current_signal`` bygges af ``title`` alene
    (``signal_tracking_framework.py:509``), og prompt-linjen læser
    ``current_signal``. En ændring af ``summary`` eller ``rationale`` når
    derfor ALDRIG modellen. Uden denne funktion gentog linjen kun fokus-laget;
    selvmodellen — den sjældne halvdel af betingelsen (36 af 632 kørsler) —
    stod ingen steder.

    Målt i de levende rækker handlede de to lag ofte slet ikke om det samme:
    «Forklarer værktøjer som Obsidian» mod «Confidence in debugging: 63%».
    Begge skrives ud, så en modsætning kan afgøres — eller afvises.
    """
    retning = ""
    for felt in ("active_focus", "active_goal", "blocked_goal"):
        item = snapshot.get(felt)
        if isinstance(item, dict):
            text = str(item.get("title") or "").strip()
            if text:
                retning = text[:64]
                break
    modpart = ""
    for felt, etiket in (
        ("active_self_model", ""),
        ("uncertain_self_model", "(usikker) "),
        ("live_reflection", "refleksion: "),
    ):
        item = snapshot.get(felt)
        if isinstance(item, dict):
            text = str(item.get("title") or "").strip()
            if text:
                modpart = f"{etiket}{text[:48]}"
                break
    if retning and modpart:
        return f"{retning} · modpart: {modpart}"
    return retning or modpart or "to lag uden læsbar tekst"
