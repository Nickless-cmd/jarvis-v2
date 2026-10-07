"""Agenter paa et klient-target: bro-invocations med ukendt udfald (agent-contract-v1 E, spec 8 + 8.1).

Et assignment bindes til ``runtime-container`` eller ``client:<stable_client_id>``. Agentens loop, modelkald,
checkpoint, inbox og vaerktoejsbeslutning bliver paa serveren; kun SELVE vaerktoejskaldet gaar over broen.

Reglerne, som koden haandhaever:

* Ejer, session og target slaas op fra det gemte assignment - ALDRIG fra kaldets argumenter. Et ufuldstaendigt
  assignment afvises; der er ingen ``_default``-session og intet fald til en anden brugers id.
* Kun ``operator_*`` kan gaa over broen, og kun til netop den bundne klient. Et vaerktoej uden for den familie
  afvises (aldrig stiltiende udfoert i containeren), og en broafbrydelse bliver aldrig til containerarbejde.
* Operator-kanalen (den aabne ``bash``-omdirigering) bruges ALDRIG af en agent: dens scope omfatter hverken
  agent, assignment eller klient, saa den kan ikke arves. Agenten bruger de eksplicitte ``operator_*``-kald.
* Hvert kald faar et stabilt ``invocation_id`` (afledt af run + tool-call-id, saa en genoptagelse genkender
  det) og skrives i DB FOER afsendelsen. Laesende kald prøves igen efter timeout; et MULIGVIS UDFOERT
  skrivende kald uden kvittering bliver ``outcome_unknown``: runnet staar stille, ingen blind retry. Kun
  klientens egen status ved reconnect eller en menneskelig afgoerelse lukker det.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
import uuid
from typing import Any

from core.runtime import db_agent_bridge as store
from core.runtime.db_agent_contract import ContractError, _conn, _now_iso

logger = logging.getLogger(__name__)

CLIENT_PREFIX = "client:"
CONTAINER = "runtime-container"
_CLIENT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,127}$")
WORKTREE_CAPABILITY = "agent_worktree"          # klienten skal annoncere den for kodeagenter (§8.1)
DEFAULT_TIMEOUT_S = 120.0
READ_RETRIES = 2                                  # laesende kald: op til 2 ekstra forsoeg efter timeout
UNSENT_RETRIES = 3                                # klient midlertidigt vaek FOER afsendelse
UNSENT_WAIT_S = 2.0

# Rent laesende (idempotente) klientvaerktoejer. ALT andet regnes som skrivende - fail-closed.
READ_TOOLS: frozenset[str] = frozenset({
    "operator_read_file", "operator_list_dir", "operator_grep", "operator_glob", "operator_screen_size",
    "operator_mouse_position", "operator_list_windows", "operator_list_processes", "operator_process_list",
    "operator_process_status", "operator_process_output", "operator_bash_output", "operator_browser_status",
    "operator_browser_get_text", "operator_browser_get_links", "operator_clipboard_read",
    "operator_scheduled_list", "operator_screenshot", "operator_screenshot_window", "operator_file_snapshot",
    "operator_watch_events", "operator_webfetch", "operator_ocr_region", "operator_find_image",
})

_BRIDGE_ERRORS = frozenset({
    "client_not_connected", "bridge_send_failed", "bridge_timeout", "bridge_disconnected",
    "bridge_call_cancelled", "bridge_forward_failed", "bridge_not_connected", "bridge_closed",
})


class BridgeHalt(RuntimeError):
    """Et skrivende kald har uafgjort udfald: agentens loop STOPPER og runnet staar i ``outcome_unknown``."""


def idempotency_class(tool: str) -> str:
    return "read" if tool in READ_TOOLS else "write"


# --------------------------------------------------------------- target


def parse_target(target: str) -> tuple[str, str]:
    """('container','') eller ('client', id). ``ValueError`` for alt andet."""
    t = str(target or "").strip() or CONTAINER
    if t == CONTAINER:
        return "container", ""
    if t.startswith(CLIENT_PREFIX):
        cid = t[len(CLIENT_PREFIX):]
        if _CLIENT_ID.match(cid) and ".." not in cid:
            return "client", cid
    raise ValueError(f"ugyldigt target {target!r}")


def check_client_target(*, owner_user_id: str, target: str, writes: bool = False) -> dict[str, Any] | None:
    """Afvisning (``{"code","detail"}``) eller ``None`` hvis klienten kan tage opgaven NU.

    Klientens tilstand tages fra broens egne annoncerede kapabiliteter - aldrig fra et argument.
    En anden af brugerens klienter er ikke en erstatning."""
    from core.services.agent_bridge_dispatch import client_info
    try:
        kind, cid = parse_target(target)
    except ValueError as exc:
        logger.info("klient-target afvist: %s", exc)
        return {"code": "INVALID_SCOPE", "detail": str(exc)}
    if kind != "client":
        return None
    info = client_info(owner_user_id, cid)
    if info is None:
        return {"code": "CLIENT_OFFLINE", "detail": f"klienten {cid!r} er ikke forbundet for ejeren"}
    caps = set(info.get("capabilities") or [])
    if not any(c.startswith("operator_") for c in caps):
        return {"code": "INVALID_SCOPE", "detail": f"klienten {cid!r} annoncerer ingen operator-vaerktoejer"}
    if writes and WORKTREE_CAPABILITY not in caps:
        return {"code": "INVALID_SCOPE",
                "detail": f"klienten {cid!r} annoncerer ikke {WORKTREE_CAPABILITY}: en kodeagent faar "
                          "intet worktree dér, og kan ikke udgive et andet arbejdsomraade for et"}
    if writes:
        # Serverens worktree-record + klientens git-handlere findes endnu ikke. Et lokalt worktree paa
        # serveren maa aldrig udgives for et klient-worktree, saa kodeagenter paa klient afvises ogsaa
        # naar kapabiliteten annonceres.
        return {"code": "INVALID_SCOPE",
                "detail": "worktree paa et klient-target er ikke bygget endnu (kun laesende/operator-agenter)"}
    return None


def allowed_tools_for_client(owner_user_id: str, target: str, requested: list[str] | None) -> list[str]:
    """Agentens vaerktoejer paa et klient-target: kun ``operator_*`` som klienten faktisk annoncerer."""
    _, cid = parse_target(target)
    from core.services.agent_bridge_dispatch import client_info
    caps = set((client_info(owner_user_id, cid) or {}).get("capabilities") or [])
    wanted = [t for t in (requested or []) if t in caps and t.startswith("operator_")]
    return sorted(wanted) if requested else sorted(c for c in caps if c in READ_TOOLS)


# --------------------------------------------------------------- identitet fra DB


def _identity(agent_id: str) -> dict[str, Any]:
    """Ejer, session, target og aktuelt run - fra DB. ``ContractError`` ved alt ufuldstaendigt."""
    conn = _conn()
    a = conn.execute("SELECT * FROM agent_assignments WHERE agent_id=? AND status IN "
                     "('queued','active','waiting') ORDER BY created_at DESC LIMIT 1", (agent_id,)).fetchone()
    if a is None:
        raise ContractError("INVALID_SCOPE", "agenten har intet aabent assignment")
    owner, session = str(a["owner_user_id"] or "").strip(), str(a["origin_session_id"] or "").strip()
    if not owner or owner == "legacy_unscoped" or not session or session in ("_default", "default"):
        raise ContractError("INVALID_SCOPE", "assignmentet mangler ejer eller session")
    run = conn.execute("SELECT run_id FROM agent_runs WHERE assignment_id=? ORDER BY attempt_no DESC LIMIT 1",
                       (a["assignment_id"],)).fetchone()
    return {"owner": owner, "session": session, "target": str(a["target"] or ""),
            "assignment_id": a["assignment_id"], "run_id": str(run["run_id"]) if run else ""}


def target_of(agent_id: str) -> tuple[str, str]:
    """('container','') / ('client', id) for agentens aabne assignment; ('container','') for en legacy-agent."""
    try:
        return parse_target(_identity(agent_id)["target"])
    except (ContractError, ValueError):
        logger.debug("agent %s har intet gyldigt klient-target - containerstien", agent_id, exc_info=True)
        return "container", ""


# --------------------------------------------------------------- sync -> async


def _run(coro: Any, timeout_s: float) -> Any:
    """Koer en coroutine fra en vilkaarlig traad. Foretraekker serverens hovedloeb (hvor WS'en bor)."""
    try:
        from core.services.jarvisx_bridge import get_main_loop
        main = get_main_loop()
    except Exception:
        logger.debug("hovedloeb utilgaengeligt", exc_info=True)
        main = None
    if main is not None and main.is_running():
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None       # ingen koerende loekke i denne traad: det er det normale ved et sync-kald
        if running is not main:
            return asyncio.run_coroutine_threadsafe(coro, main).result(timeout=timeout_s + 15)
    return asyncio.run(coro)


def _invocation_id(run_id: str, call_id: str) -> str:
    if not call_id:
        return f"inv-{uuid.uuid4().hex}"
    return "inv-" + hashlib.sha256(f"{run_id}|{call_id}".encode()).hexdigest()[:32]


def _clean_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Myndighed kommer fra serveren. Alt modellen har skrevet med foranstillet underscore fjernes."""
    return {k: v for k, v in arguments.items() if not str(k).startswith("_")}


def _tool_error(code: str, detail: str, **extra: Any) -> str:
    return json.dumps({"status": "error", "code": code, "phase": "bridge", "error": detail, **extra},
                      ensure_ascii=False)


# --------------------------------------------------------------- selve kaldet


def invoke_tool_call(*, agent: dict[str, Any], run_id: str, tc: dict[str, Any],
                     dispatch: Any = None, sleep: Any = time.sleep) -> str | None:
    """Udfoer ET agent-vaerktoejskald paa den bundne klient. ``None`` = agenten er ikke paa et klient-target
    (kalderen koerer vaerktoejet som hidtil). Ellers tool-resultatet som JSON-streng; rejser ``BridgeHalt``
    naar udfaldet af et skrivende kald er uafgjort. ``dispatch`` er sømmen til broen (tests)."""
    agent_id = str(agent.get("agent_id") or "")
    try:
        ident = _identity(agent_id)
        kind, client_id = parse_target(ident["target"])
    except ContractError as exc:
        logger.debug("agent %s: ingen bro-identitet (%s)", agent_id, exc.detail)
        # En legacy-agent har intet assignment: den koerer containerstien. En bundet agent med et
        # ufuldstaendigt assignment afvises hoejt - men kun hvis den overhovedet er bundet.
        from core.services.agent_model_router import bound_owner
        return _tool_error("INVALID_SCOPE", exc.detail) if bound_owner(agent_id) else None
    except ValueError as exc:
        logger.warning("agent %s har et ugyldigt target: %s", agent_id, exc)
        return _tool_error("INVALID_SCOPE", str(exc))
    if kind != "client":
        return None
    fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
    tool = str(fn.get("name") or "").strip()
    if not tool.startswith("operator_"):
        # Ingen stille tilbagegang til containeren: et ikke-klientvaerktoej er afvist paa et klient-target.
        return _tool_error("POLICY_DENIED", f"{tool or '(intet navn)'} kan ikke koeres paa et klient-target")
    raw = fn.get("arguments")
    try:
        args = json.loads(raw) if isinstance(raw, str) and raw.strip() else (dict(raw) if isinstance(raw, dict) else {})
    except ValueError:
        logger.warning("agent %s sendte ugyldig JSON som vaerktoejsargumenter", agent_id)
        return _tool_error("INVALID_SCOPE", "vaerktoejsargumenterne er ikke gyldig JSON")
    args = _clean_args(args)
    sticky = store.unknown_for_assignment(ident["assignment_id"])
    if sticky:
        # Et tidligere skrivende kald er uafgjort: INTET nyt maa ud til klienten, og loekken stoppes igen.
        raise _halt(ident, sticky[0])
    klass = idempotency_class(tool)
    try:
        row = store.begin(invocation_id=_invocation_id(ident["run_id"], str(tc.get("id") or "")),
                          owner_user_id=ident["owner"], origin_session_id=ident["session"], agent_id=agent_id,
                          assignment_id=ident["assignment_id"], run_id=ident["run_id"], client_id=client_id,
                          tool=tool, idem_class=klass, args=args)
    except ContractError as exc:
        logger.warning("bro-kald afvist for agent %s: %s %s", agent_id, exc.code, exc.detail)
        return _tool_error(exc.code, exc.detail)
    if row["state"] in (store.SUCCEEDED, store.VERIFIED_EXECUTED):
        return json.dumps({"status": "ok", "result": _loads(row["result_json"]), "replayed": True},
                          ensure_ascii=False, default=str)
    if row["state"] != store.PENDING and row["state"] != store.SENT:
        if row["state"] == store.UNKNOWN:
            raise _halt(ident, row)
        return _tool_error("BRIDGE_CALL_FINAL", f"kaldet er allerede afgjort ({row['state']})",
                           invocation_id=row["invocation_id"], error_detail=row["error"])
    return _drive(ident=ident, agent_id=agent_id, row=row, client_id=client_id, tool=tool, args=args,
                  klass=klass, dispatch=dispatch, sleep=sleep)


def _drive(*, ident: dict[str, Any], agent_id: str, row: dict[str, Any], client_id: str, tool: str,
           args: dict[str, Any], klass: str, dispatch: Any, sleep: Any) -> str:
    from core.services.agent_bridge_dispatch import dispatch_pinned
    send = dispatch or dispatch_pinned
    iid = row["invocation_id"]
    extra = {"invocation_id": iid, "run_id": ident["run_id"], "assignment_id": ident["assignment_id"],
             "idempotency_class": klass}
    unsent = 0
    timeouts = 0
    while True:
        store.mark_sent(iid)
        try:
            res = _run(send(user_id=ident["owner"], client_id=client_id, tool=tool, args=args,
                            timeout_s=DEFAULT_TIMEOUT_S, extra=extra), DEFAULT_TIMEOUT_S)
        except Exception as exc:
            logger.warning("bro-dispatch for %s fejlede: %s", iid, exc, exc_info=True)
            res = {"status": "error", "error": "bridge_forward_failed", "sent": None, "detail": str(exc)[:160]}
        if res.get("status") == "ok":
            store.finish(iid, ok=True, result=res.get("result"))
            return json.dumps({"status": "ok", "result": res.get("result"), "invocation_id": iid},
                              ensure_ascii=False, default=str)
        err = str(res.get("error") or "")
        if err not in _BRIDGE_ERRORS:
            # Klientens handler SVAREDE med en fejl: kaldet er afgjort (udfoert med fejl).
            store.finish(iid, ok=False, error=err)
            return _tool_error("TOOL_FAILED", err[:300], invocation_id=iid)
        if res.get("sent") is False:
            store.unmark_sent(iid)                       # intet forlod serveren
            unsent += 1                                  # sikkert at vente og proeve igen
            if unsent > UNSENT_RETRIES:
                store.abort_unsent(iid, err)
                return _tool_error("CLIENT_OFFLINE", f"klienten {client_id!r} kunne ikke naas ({err})",
                                   invocation_id=iid)
            sleep(UNSENT_WAIT_S)
            continue
        # Muligvis afsendt uden kvittering: timeout, afbrudt bro eller forward-fejl.
        if klass == "read" and timeouts < READ_RETRIES:
            timeouts += 1
            continue
        store.mark_unknown(iid, err)
        raise _halt(ident, store.get(iid) or row)


def _loads(text: str) -> Any:
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        logger.debug("gemt resultat er ikke JSON - returneres som tekst")
        return text


def _halt(ident: dict[str, Any], row: dict[str, Any]) -> BridgeHalt:
    """Sæt run + assignment i ``outcome_unknown``/``waiting`` (som lease-reconcileren gør) og returner halten."""
    conn = _conn()
    now = _now_iso()
    conn.execute("UPDATE agent_runs SET status='outcome_unknown', failure_reason=?, error_phase='bridge', "
                 "error_code='OUTCOME_UNKNOWN', updated_at=? WHERE run_id=?",
                 (f"bro-kald {row['invocation_id']} ({row['tool']}) uden kvittering", now, ident["run_id"]))
    conn.execute("UPDATE agent_assignments SET status='waiting', updated_at=? WHERE assignment_id=? "
                 "AND status IN ('queued','active')", (now, ident["assignment_id"]))
    from core.runtime.db_agent_outcome_unknown import notify_outcome_unknown, publish_outcome_unknown
    notify_outcome_unknown(conn, assignment_id=ident["assignment_id"], run_id=ident["run_id"],
                           reason=f"bro-kald {row['invocation_id']} ({row['tool']}) uden kvittering", open_tool_calls=1)
    conn.commit()
    publish_outcome_unknown(assignment_id=ident["assignment_id"], run_id=ident["run_id"], agent_id=row["agent_id"],
                            owner_user_id=row["owner_user_id"])
    try:
        from core.runtime.db_agent_runtime import update_agent_registry_entry
        update_agent_registry_entry(row["agent_id"], status="outcome_unknown",
                                    last_error=f"OUTCOME_UNKNOWN: {row['tool']} paa klienten er uafgjort")
    except Exception:
        logger.warning("agentens status kunne ikke saettes til outcome_unknown", exc_info=True)
    return BridgeHalt(f"OUTCOME_UNKNOWN:{row['invocation_id']}")


def run_is_halted(run_id: str) -> bool:
    r = _conn().execute("SELECT status FROM agent_runs WHERE run_id=?", (run_id,)).fetchone()
    return bool(r) and r["status"] == "outcome_unknown"


# --------------------------------------------------------------- afgoerelse


def _settle_resolved(row: dict[str, Any], verdict: str, *, actor_kind: str, decided_by: str) -> None:
    """Et uafgjort kald er nu afgjort: assignmentet afsluttes via den ENE vej der maa lukke et uvist udfald
    (``resolve_outcome_unknown``: kun menneske eller verificering, praecis én terminalbesked). Intet genudfoeres -
    parenten/brugeren beslutter selv en opfoelgning, og faktaene staar i terminalbeskeden."""
    from core.runtime.db_agent_outcome_unknown import resolve_outcome_unknown

    a = _conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                        (row["assignment_id"],)).fetchone()
    if a is None or a["status"] != "waiting":
        return
    facts = (f"{row['tool']} ({row['invocation_id']}) paa klienten {row['client_id']} {verdict}. "
             "Intet er genudfoert; vurder selv en opfoelgning.")
    try:
        resolve_outcome_unknown(owner_user_id=row["owner_user_id"], assignment_id=row["assignment_id"],
                                outcome="failed", decided_by=decided_by, actor_kind=actor_kind, note=facts)
    except ContractError as exc:
        logger.warning("uvist udfald for %s kunne ikke afgoeres: %s %s", row["assignment_id"], exc.code, exc.detail)


def apply_client_report(*, owner_user_id: str, client_id: str, reports: list[dict[str, Any]]) -> dict[str, str]:
    """Klientens egen status ved reconnect (kaldes af WS-ruten)."""
    out = store.apply_client_report(owner_user_id=owner_user_id, client_id=client_id, reports=reports)
    for iid, verdict in out.items():
        if verdict in (store.VERIFIED_EXECUTED, store.VERIFIED_NOT_EXECUTED):
            row = store.get(iid)
            if row is not None:
                _settle_resolved(row, "var udfoert" if verdict == store.VERIFIED_EXECUTED else "blev IKKE udfoert",
                                 actor_kind="verifier", decided_by=f"client:{client_id}")
    return out


def human_resolve(*, invocation_id: str, owner_user_id: str, executed: bool, actor_user_id: str) -> dict[str, Any]:
    row = store.human_resolve(invocation_id=invocation_id, owner_user_id=owner_user_id, executed=executed,
                              actor_user_id=actor_user_id)
    _settle_resolved(row, "er af brugeren afgjort som udfoert" if executed else "er af brugeren afgjort som ikke udfoert",
                     actor_kind="human", decided_by=actor_user_id)
    return row



def status_query_for(owner_user_id: str, client_id: str) -> list[str]:
    """Invocation-id'er klienten skal oplyse status for ved reconnect."""
    return [r["invocation_id"] for r in store.unresolved_for_client(owner_user_id, client_id)]
