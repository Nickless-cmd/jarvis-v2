"""In-flight run tracker for resume-after-interrupt.

When a visible run starts, we drop a small record on disk. When it
completes (success OR fail OR cancel), we clear it. If a record
survives to the next visible turn for the same session, the prompt
assembler surfaces it as: "Du blev afbrudt midt i: <excerpt>" so the
model can ask the user whether to continue or restart.

Without this, a service restart, browser crash, or unhandled exception
silently drops whatever Jarvis was working on — the user has no signal
to follow up, and Jarvis has no memory of the dropped task. The whole
agentic-parity stack is undermined when interrupted work just vanishes.

Pattern follows phase 0's state_store (atomic JSON file).
"""
from __future__ import annotations

import logging
import os
import fcntl
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime import state_store

logger = logging.getLogger(__name__)

_STATE_KEY = "in_flight_runs"
_EXCERPT_LIMIT = 240
# A run that's been "in flight" for less than this is probably just still
# streaming on another worker, NOT actually interrupted. Avoid the false
# positive where the next user message races the previous run's finally
# block.
_MIN_AGE_TO_SURFACE_SECONDS = 90
_RESUME_WORDS = (
    "fortsæt", "fortsaet", "prøv igen", "prov igen", "igen", "go on",
    "continue", "resume", "samle op", "kør videre", "kor videre",
)
_RESTART_WORDS = (
    "start forfra", "ny opgave", "glem den", "drop den", "restart",
    "start over", "ignore previous", "glem det",
)

_TERMINAL_STATUSES = {"completed", "cancelled", "failed_terminal"}


class StaleRecoveryClaim(RuntimeError):
    """A superseded recovery generation attempted to mutate durable truth."""


@contextmanager
def _med_laas():
    """Serialize recovery-journal read/modify/write across API and runtime."""
    path = state_store._path(_STATE_KEY).with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


# ── Ejer-identitet (12/9-2026) ───────────────────────────────────────────────
# Hvorfor: api- og runtime-processen kører SAMME app (`apps.api.jarvis_api.app:app`)
# mod SAMME delte `in_flight_runs.json`. Uden en ejer på posten kunne den ene
# proses nedluknings-sweep stemple den andens aktive ture — målt på
# `visible-d1fa743d`, der stod `interrupted`/`api-nedlukning` kl. 17:39:47 mens
# den kørte videre og sluttede `completed` 17:43:08. Flaget målte «min proces
# lukker», ikke «dette run er dødt».


def _proc_start_ticks(pid: int) -> str | None:
    """Start-tid for ``pid`` (Linux: ``/proc/<pid>/stat`` felt 22).

    Tre udfald, og forskellen er hele pointen:
    ``None`` = processen findes ikke (bevis) · ``""`` = findes, men vi kunne
    ikke læse starttiden (et spørgsmål) · ellers selve start-tiden.

    Hvorfor ikke bare pid'en: Linux genbruger pid'er. Uden start-tiden kunne en
    post fra en død proces se ud som om den tilhørte en helt ny proces med samme
    pid — og så ville sweepen stemple en levende turs post, eller lade en ægte
    zombie ligge.
    """
    try:
        with open(f"/proc/{pid}/stat", "rb") as f:
            data = f.read()
    except FileNotFoundError:
        return None
    except Exception:
        return ""
    try:
        # ``comm`` (felt 2) kan indeholde både mellemrum og parenteser, så vi
        # splitter efter den SIDSTE ')'. Derefter starter felt 3 ved index 0 —
        # og felt 22 (starttime) er index 19.
        return data.rsplit(b")", 1)[1].split()[19].decode()
    except Exception:
        return ""


def current_owner() -> str:
    """Denne proces' identitet: ``<pid>:<starttime>``.

    Skrives på hver in-flight-post, så posten bærer HVEM der ejer den — ikke kun
    hvornår den blev skrevet.
    """
    pid = os.getpid()
    return f"{pid}:{_proc_start_ticks(pid) or ''}"


def owner_still_alive(owner: str) -> bool | None:
    """Kører den proces der ejer posten stadig?

    ``True`` = lever · ``False`` = væk · ``None`` = kunne ikke afgøres.
    ``None`` er ikke ``False``: en post vi ikke kan afgøre ejerskabet på må ikke
    stemples på et gæt.
    """
    if not owner:
        return None
    pid_str, _, start = str(owner).partition(":")
    try:
        pid = int(pid_str)
    except Exception:
        return None
    if pid <= 0:
        return None
    nuvaerende = _proc_start_ticks(pid)
    if nuvaerende is None:
        return False                    # processen findes ikke → ejeren er væk
    if nuvaerende == "":
        return None                     # findes måske — vi kunne ikke læse den
    if not start:
        return True                     # ingen starttid at sammenligne med
    return nuvaerende == start          # samme pid, NY starttid = genbrugt pid


def _load() -> dict[str, dict[str, Any]]:
    raw = state_store.load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            out[str(k)] = v
    return out


def _save(records: dict[str, dict[str, Any]]) -> None:
    state_store.save_json_strict(_STATE_KEY, records)


def _mutate(fn):
    with _med_laas():
        records = _load()
        result = fn(records)
        _save(records)
        return result


def _record_key(records: dict[str, dict[str, Any]], identity: str) -> str | None:
    value = str(identity or "")
    if value in records:
        return value
    for key, rec in records.items():
        if value in {str(rec.get("task_id") or ""), str(rec.get("run_id") or "")}:
            return key
    return None


def _iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).isoformat()


def _parsed(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or ""))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except Exception:
        return None


def _check_claim(
    rec: dict[str, Any], *, expected_generation: int | None, expected_owner: str,
) -> None:
    if expected_generation is not None and int(
        rec.get("recovery_generation") or 0
    ) != int(expected_generation):
        raise StaleRecoveryClaim("recovery generation was superseded")
    if expected_owner and str(rec.get("recovery_owner") or "") != str(expected_owner):
        raise StaleRecoveryClaim("recovery owner was superseded")


def mark_started(
    *,
    run_id: str,
    session_id: str | None,
    user_message: str,
    kind: str = "visible",
    provider: str = "",
    model: str = "",
    task_id: str = "",
    recovery_generation: int = 0,
    recovery_attempt: int = 0,
    recovery_limit: int = 3,
) -> None:
    """Record that a run is in flight. Keyed by run_id (unique).

    Side effect: clears any prior in_flight records for the same session.
    A new turn implies the previous turn finished (or won't finish) — keep
    only the most recent so the digest never sees zombies left behind by
    crashes, killed runs, or finally-blocks that didn't complete.

    ``kind`` (visible|autonomous|heartbeat, default visible), ``provider`` and
    ``model`` are additive, backward-compatible metadata: existing callers that
    omit them get the visible/empty defaults. The boot-reconciler uses them to
    describe which kinds of run were orphaned by a crash.

    ``owner_proc`` (12/9-2026) er denne proces' identitet (pid + starttid).
    Uden den kunne en nedluknings-sweep i én proces stemple en aktiv tur i en
    anden — begge services kører samme app mod samme delte fil. Poster uden
    feltet (ældre, eller skrevet af en test) falder tilbage til alders-filteret.
    """
    if not run_id:
        return
    sid = str(session_id or "")
    def change(records):
        records[str(run_id)] = {
            "task_id": str(task_id or run_id),
            "run_id": str(run_id),
            "session_id": sid,
            "status": "running",
            "kind": str(kind or "visible"),
            "provider": str(provider or ""),
            "model": str(model or ""),
            "excerpt": (user_message or "")[:_EXCERPT_LIMIT],
            "original_request": str(user_message or ""),
            "started_at": _iso(),
            "last_progress_at": _iso(),
            "last_tool": "",
            "owner_proc": current_owner(),
            "recovery_generation": max(0, int(recovery_generation)),
            "recovery_attempt": max(0, int(recovery_attempt)),
            "recovery_limit": max(0, int(recovery_limit)),
            "recovery_owner": "",
            "recovery_lease_until": "",
            "next_attempt_at": "",
            "notice_pending": False,
        }
    _mutate(change)


def mark_tool(run_id: str, tool_name: str) -> None:
    """Update the last-tool-attempted hint for an in-flight run."""
    if not run_id or not tool_name:
        return
    def change(records):
        key = _record_key(records, run_id)
        if key is not None:
            records[key]["last_tool"] = str(tool_name)[:80]
            records[key]["last_progress_at"] = _iso()
    _mutate(change)


def mark_completed(run_id: str) -> None:
    """Clear an in-flight record on success/fail/cancel — all the same to us;
    only *unresolved* records should reach the next prompt build."""
    if not run_id:
        return
    def change(records):
        key = _record_key(records, run_id)
        if key is not None:
            records.pop(key, None)
    _mutate(change)


def mark_interrupted(run_id: str, *, reason: str = "", summary: str = "") -> None:
    """Keep an in-flight record as a resumable interrupted run."""
    if not run_id:
        return
    def change(records):
        key = _record_key(records, run_id)
        if key is None:
            return
        rec = records[key]
        rec["status"] = "interrupted"
        rec["interruption_reason"] = str(reason or "")[:120]
        rec["interruption_summary"] = str(summary or "")[:240]
        rec["interrupted_at"] = _iso()
    _mutate(change)


def settle_recovering(
    run_id: str,
    *,
    reason: str,
    summary: str = "",
    checkpoint_ref: str = "",
    recovery_limit: int = 3,
    expected_generation: int | None = None,
    expected_owner: str = "",
) -> dict[str, Any]:
    """Durably make a run claimable without erasing its task identity."""
    def change(records):
        key = _record_key(records, run_id)
        if key is None:
            raise KeyError(f"unknown in-flight run: {run_id}")
        rec = records[key]
        _check_claim(
            rec,
            expected_generation=expected_generation,
            expected_owner=expected_owner,
        )
        now = _iso()
        rec.setdefault("task_id", str(rec.get("run_id") or key))
        rec["status"] = "recovering"
        rec["exit_reason"] = str(reason or "unknown")[:160]
        rec["interruption_reason"] = rec["exit_reason"]
        rec["interruption_summary"] = str(summary or reason or "")[:500]
        rec["checkpoint_ref"] = str(checkpoint_ref or rec.get("checkpoint_ref") or "")
        rec["recovery_limit"] = max(0, int(recovery_limit))
        rec.setdefault("recovery_attempt", 0)
        rec.setdefault("recovery_generation", 0)
        rec["settled_at"] = now
        rec["interrupted_at"] = now
        rec["notice_pending"] = True
        rec["recovery_owner"] = ""
        rec["recovery_lease_until"] = ""
        rec.setdefault("next_attempt_at", "")
        return dict(rec)
    return _mutate(change)


def settle_terminal(
    run_id: str,
    *,
    status: str,
    reason: str = "",
    expected_generation: int | None = None,
    expected_owner: str = "",
) -> dict[str, Any] | None:
    """Persist a genuine terminal state and revoke every recovery claim."""
    normalized = str(status or "")
    if normalized not in _TERMINAL_STATUSES:
        raise ValueError(f"invalid terminal status: {normalized}")

    def change(records):
        key = _record_key(records, run_id)
        if key is None:
            return None
        rec = records[key]
        _check_claim(
            rec,
            expected_generation=expected_generation,
            expected_owner=expected_owner,
        )
        rec.setdefault("task_id", str(rec.get("run_id") or key))
        rec["status"] = normalized
        rec["exit_reason"] = str(reason or normalized)[:160]
        rec["settled_at"] = _iso()
        rec["recovery_owner"] = ""
        rec["recovery_lease_until"] = ""
        rec["next_attempt_at"] = ""
        rec["notice_pending"] = normalized == "failed_terminal"
        return dict(rec)
    return _mutate(change)


def claim_due_recovery(
    *,
    owner: str,
    lease_seconds: float = 120.0,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Atomically claim one due visible recovery task."""
    instant = now or datetime.now(UTC)

    def change(records):
        candidates: list[tuple[str, dict[str, Any]]] = []
        for key, rec in records.items():
            if str(rec.get("kind") or "visible") != "visible":
                continue
            status = str(rec.get("status") or "")
            if status == "recovering":
                pass
            elif status == "running" and rec.get("recovery_owner"):
                lease = _parsed(rec.get("recovery_lease_until"))
                if lease is not None and lease > instant:
                    continue
            else:
                continue
            due = _parsed(rec.get("next_attempt_at"))
            if due is not None and due > instant:
                continue
            if int(rec.get("recovery_attempt") or 0) >= int(
                rec.get("recovery_limit") or 3
            ):
                continue
            candidates.append((key, rec))
        if not candidates:
            return None
        key, rec = min(
            candidates,
            key=lambda item: str(
                item[1].get("settled_at") or item[1].get("started_at") or ""
            ),
        )
        rec.setdefault("task_id", str(rec.get("run_id") or key))
        rec["status"] = "running"
        rec["recovery_generation"] = int(rec.get("recovery_generation") or 0) + 1
        rec["recovery_attempt"] = int(rec.get("recovery_attempt") or 0) + 1
        rec["recovery_owner"] = str(owner)
        rec["owner_proc"] = str(owner)
        rec["recovery_claimed_at"] = instant.isoformat()
        rec["recovery_lease_until"] = (
            instant + timedelta(seconds=max(1.0, float(lease_seconds)))
        ).isoformat()
        rec["next_attempt_at"] = ""
        return dict(rec)
    return _mutate(change)


def renew_recovery_lease(
    task_id: str,
    generation: int,
    *,
    owner: str,
    lease_seconds: float = 120.0,
    now: datetime | None = None,
) -> bool:
    instant = now or datetime.now(UTC)

    def change(records):
        key = _record_key(records, task_id)
        if key is None:
            return False
        rec = records[key]
        if (
            str(rec.get("recovery_owner") or "") != str(owner)
            or int(rec.get("recovery_generation") or 0) != int(generation)
            or str(rec.get("status") or "") != "running"
        ):
            return False
        rec["recovery_lease_until"] = (
            instant + timedelta(seconds=max(1.0, float(lease_seconds)))
        ).isoformat()
        rec["last_progress_at"] = instant.isoformat()
        return True
    return bool(_mutate(change))


def release_recovery_claim(
    task_id: str,
    generation: int,
    *,
    owner: str,
    reason: str,
    retry_after_s: float,
    now: datetime | None = None,
) -> bool:
    instant = now or datetime.now(UTC)

    def change(records):
        key = _record_key(records, task_id)
        if key is None:
            return False
        rec = records[key]
        if (
            str(rec.get("recovery_owner") or "") != str(owner)
            or int(rec.get("recovery_generation") or 0) != int(generation)
        ):
            return False
        rec["status"] = "recovering"
        rec["exit_reason"] = str(reason or "recovery-dispatch-failed")[:160]
        rec["recovery_owner"] = ""
        rec["recovery_lease_until"] = ""
        rec["next_attempt_at"] = (
            instant + timedelta(seconds=max(0.0, float(retry_after_s)))
        ).isoformat()
        rec["notice_pending"] = True
        return True
    return bool(_mutate(change))


# En afbrudt tur er en genoptagelses-kandidat i timer, ikke i uger. FOER havde
# `interrupted_for_session` INGEN aldersgraense: den returnerede den nyeste
# `interrupted`-post for en session for evigt, og baade `resume_context` og selve
# prompt-teksten («du blev afbrudt») hang paa den. En post der aldrig aeldes ville
# altsaa blive tilbudt som genoptagelse i det uendelige. (Jarvis' fund, 11/9-2026.)
GENOPTAGELSES_VINDUE_TIMER = 24.0


def _friskere_end(rec: dict[str, Any], graense: datetime) -> bool:
    """Er posten ung nok til at vaere en genoptagelses-kandidat?

    Bruger `interrupted_at` naar den findes, ellers `started_at`. Kan tiden
    ikke laeses, svarer vi True: en post vi ikke kan datere maa ikke forsvinde
    tavst — fravaer af tidsstempel er ikke bevis for aelde.
    """
    ulaeselige: list[str] = []
    for felt in ("interrupted_at", "started_at"):
        raa = str(rec.get(felt) or "").strip()
        if not raa:
            continue
        try:
            t = datetime.fromisoformat(raa)
        except Exception:
            ulaeselige.append(f"{felt}={raa!r}")
            continue
        if t.tzinfo is None:
            t = t.replace(tzinfo=UTC)
        return t >= graense
    # Retningen er rigtig — vi bevarer frem for at smide vaek — men den maa
    # ikke vaere TAVS. Var der et tidsstempel som `fromisoformat` ikke kunne
    # laese, er posten en evighedskandidat, og ingen ville opdage det.
    # `mark_interrupted` skriver altid `interrupted_at`, saa dette er den
    # defensive gren: rammer den, er der sket noget med formatet.
    # (Jarvis' indvending, 11/9-2026.)
    if ulaeselige:
        logger.warning(
            "in-flight-post kunne ikke dateres — beholdes som "
            "genoptagelses-kandidat uden aldersgraense: run=%s session=%s %s",
            rec.get("run_id", "?"), rec.get("session_id", "?"),
            " ".join(ulaeselige))
    return True


def interrupted_for_session(session_id: str | None) -> dict[str, Any] | None:
    """Return the most recent in-flight record for this session, or None.

    "Most recent" matters because a brief race during normal completion can
    leave a stale record momentarily; the freshest one is the most likely
    candidate for "this is what I was doing".
    """
    if not session_id:
        return None
    sid = str(session_id)
    graense = datetime.now(UTC) - timedelta(hours=GENOPTAGELSES_VINDUE_TIMER)
    records = _load()
    candidates = [
        r for r in records.values()
        if r.get("session_id") == sid
        # `or "interrupted"` FOER: en post UDEN status talte som afbrudt. En
        # default der laeses som en dom — samme figur som `holder: True` ved
        # nul kontrollerede paastande. Nu kraeves det udtrykkeligt.
        and str(r.get("status") or "") == "interrupted"
        and _friskere_end(r, graense)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda r: str(r.get("started_at", "")), reverse=True)
    return candidates[0]


def list_running_orphans(
    stale_after_s: float,
    *,
    dying_owner: str | None = None,
) -> list[dict[str, Any]]:
    """Return ``running`` records whose OWNER is gone — i.e. genuine zombies.

    Hvem er en forladt post? (12/9-2026.) Før var svaret «enhver ``running``-post
    ældre end ``stale_after_s``». Det er et svar om TID, ikke om ejerskab — og
    api- og runtime-processen kører SAMME app mod SAMME delte ``in_flight_runs``.
    En nedlukning af den ene stemplede derfor den andens aktive ture: målt på
    ``visible-d1fa743d``, der stod ``interrupted``/``api-nedlukning`` kl. 17:39:47
    mens den kørte videre og sluttede ``completed`` 17:43:08.

    Reglen er nu, pr. post med et ``owner_proc``:

    - ejeren ER ``dying_owner`` (os selv, vi er ved at lukke) → forladt, stempl.
    - ejeren lever → IKKE forladt. Det er søster-processens tur, ikke vores.
    - ejeren er væk → forladt (crash).
    - ejerskabet kan ikke afgøres, eller posten har slet ingen ejer (ældre post,
      eller skrevet af en test) → alders-filteret afgør, præcis som før.
      Bagudkompatibelt: ingen eksisterende kald ændrer adfærd for sådanne poster.

    Pure read (no writes). Records med et ``started_at`` vi ikke kan læse
    rapporteres konservativt IKKE — vi stempler kun en post vi kan bekræfte.
    """
    now = datetime.now(UTC)
    out: list[dict[str, Any]] = []
    for rec in _load().values():
        if str(rec.get("status") or "running") != "running":
            continue
        started_iso = str(rec.get("started_at") or "")
        if not started_iso:
            continue
        try:
            started_dt = datetime.fromisoformat(started_iso)
        except Exception:
            continue
        gammel_nok = (now - started_dt).total_seconds() >= float(stale_after_s)

        owner = str(rec.get("owner_proc") or "")
        if owner:
            if dying_owner and owner == str(dying_owner):
                out.append(rec)      # os selv — vi er ved at dø
                continue
            alive = owner_still_alive(owner)
            if alive is False:
                out.append(rec)      # ejeren er væk = ægte zombie
                continue
            if alive is True:
                continue             # lever — ikke vores at stemple
            # alive is None → kunne ikke afgøres; alderen afgør nedenfor.
        if gammel_nok:
            out.append(rec)
    return out


def clear_session(session_id: str | None) -> int:
    """Drop all in-flight records for a session (used when user explicitly
    says 'restart' / 'forget that')."""
    if not session_id:
        return 0
    sid = str(session_id)
    def change(records):
        to_drop = [k for k, v in records.items() if v.get("session_id") == sid]
        for key in to_drop:
            records.pop(key, None)
        return len(to_drop)
    return int(_mutate(change))


def classify_resume_intent(user_message: str) -> str:
    """Classify whether a user message should resume an interrupted run."""
    normalized = " ".join(str(user_message or "").strip().lower().split())
    if not normalized:
        return "unclear"
    if any(word in normalized for word in _RESTART_WORDS):
        return "restart"
    if any(word in normalized for word in _RESUME_WORDS):
        return "resume"
    return "unclear"


def interruption_prompt_section(
    session_id: str | None,
    user_message: str = "",
) -> str | None:
    """Format an interrupted record as a system-prompt block, or None.

    Race-aware: only surfaces if the in_flight record is older than
    _MIN_AGE_TO_SURFACE_SECONDS. The previous run's finally-block (which
    calls mark_completed) runs *after* the [DONE] event reaches the
    client, so a fast follow-up message can race the cleanup. A genuine
    interruption (crash, restart) leaves the record older than the
    threshold and surfaces correctly.
    """
    rec = interrupted_for_session(session_id)
    if not rec:
        return None
    intent = classify_resume_intent(user_message)
    if intent == "restart":
        return None
    started_iso = str(rec.get("started_at") or "")
    if started_iso:
        try:
            started_dt = datetime.fromisoformat(started_iso)
            age = (datetime.now(UTC) - started_dt).total_seconds()
            if age < _MIN_AGE_TO_SURFACE_SECONDS:
                return None
        except Exception:
            pass
    excerpt = str(rec.get("excerpt") or "(intet uddrag)")
    last_tool = str(rec.get("last_tool") or "")
    reason = str(rec.get("interruption_reason") or "")
    started_at = started_iso[11:19] if started_iso else ""
    tool_clause = f" — sidste tool var {last_tool}" if last_tool else ""
    reason_clause = f" Årsag: {reason}." if reason else ""
    checkpoint = ""
    try:
        from core.services.agentic_checkpoints import checkpoint_prompt_section
        checkpoint = checkpoint_prompt_section(session_id) or ""
    except Exception:
        checkpoint = ""
    conclusion = ""
    try:
        from core.services.agentic_working_conclusions import working_conclusion_prompt_section
        conclusion = working_conclusion_prompt_section(session_id) or ""
    except Exception:
        conclusion = ""
    if intent == "resume":
        policy = (
            "AUTO-RESUME: Brugerens besked betyder fortsæt/prøv igen. "
            "Fortsæt fra checkpointet uden at spørge først, og undgå at gentage allerede udførte tools medmindre inputfilerne er ændret."
        )
    else:
        policy = (
            "Intent er ikke tydelig resume. Spørg kort om du skal fortsætte fra checkpointet eller starte forfra, før du bruger mere tool-budget."
        )
    return (
        "Du blev afbrudt midt i en opgave (startet "
        f"{started_at}{tool_clause}):\n"
        f"  \"{excerpt}\"\n"
        f"{reason_clause}\n"
        f"{checkpoint + chr(10) if checkpoint else ''}"
        f"{conclusion + chr(10) if conclusion else ''}"
        f"{policy}"
    )

