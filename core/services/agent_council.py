"""Raad og review-kaede paa agentmotoren (agent-contract-v1 F5, spec 5.1 / 7.1 / 11).

Et raad er et moenster over de almindelige assignments - ingen egen LLM-runtime og ingen ThreadPool:

* ét assignment pr. medlem, alle med SAMME faktagrundlag men hver sin vurderingsopgave, i adskilte kontekster;
* et saerskilt syntese-assignment, oprettet FOERST naar ALLE medlemmer er terminale (``advance``, koert af
  supervisoren). Et fejlet medlem taeller som terminalt, og syntesen faar det NAVNGIVET - den maa ikke tie om det;
* parenten vaekkes af en ventekontrakt paa syntesen (ikke paa medlemmerne), saa Jarvis faar ét samlet svar.

Hele raadet accepteres eller intet: er der ikke plads til alle medlemmer, eller svigter en dispatch undervejs,
afbrydes de allerede startede og raadet er ``cancelled`` (intet halvt raad).

Review-kaeden (``dispatch_review``): en uafhaengig, skrivebeskyttet reviewer faar kravet, builderens FAKTISKE
aendringer (diff, filliste) og dens artefakter - builderens egen konklusion medfoelger, men mærket som en
PAASTAND der skal efterproeves, aldrig som sandhed.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.runtime import db_agent_artifacts as art
from core.runtime import db_agent_council as store
from core.runtime.db_agent_contract import ASSIGNMENT_TERMINAL, ContractError, _conn
from core.services import agent_contract_service as svc

logger = logging.getLogger(__name__)

MIN_MEMBERS, MAX_MEMBERS = 2, 6                    # seks medlemmer passer i kapacitetsprofilen (§12.3)
MEMBER_SUMMARY_CHARS = 1500
EVIDENCE_DIFF_CHARS = 20_000
MEMBER_GOAL_HEAD = ("Du er raadsmedlem {i} af {n} ({role}). Giv din SELVSTAENDIGE vurdering ud fra faktagrundlaget "
                    "nedenfor og din egen opgave. Du kender ikke de andre medlemmers svar; det er meningen. "
                    "Angiv konfidens og hvad du ikke kunne verificere.")
_err = svc._err


def _digest(topic: str, members: list[dict[str, str]]) -> str:
    return json.dumps({"t": topic, "m": [(m["role"], m["task"]) for m in members]}, ensure_ascii=False, sort_keys=True)


def _validate(members: Any) -> tuple[list[dict[str, str]], str]:
    if not isinstance(members, list) or not (MIN_MEMBERS <= len(members) <= MAX_MEMBERS):
        return [], f"et raad kraever {MIN_MEMBERS}-{MAX_MEMBERS} medlemmer"
    out: list[dict[str, str]] = []
    for m in members:
        role = str((m or {}).get("role") or "").strip() if isinstance(m, dict) else ""
        task = str((m or {}).get("task") or "").strip() if isinstance(m, dict) else ""
        if not role or not task:
            return [], "hvert medlem kraever role og task"
        out.append({"role": role, "task": task})
    if len({m["task"] for m in out}) != len(out):
        return [], "medlemmerne skal have forskellige vurderingsopgaver (ellers er det ét svar talt flere gange)"
    return out, ""


def _room_for(owner: str, parent: str, n: int) -> dict[str, Any] | None:
    from core.runtime import db_agent_contract as c
    for count, cap, what in ((c.count_open_assignments(), svc.MAX_ACTIVE_GLOBAL, "globalt"),
                             (c.count_open_assignments(owner_user_id=owner), svc.MAX_ACTIVE_PER_OWNER, "pr. ejer"),
                             (c.count_open_assignments(parent_agent_id=parent), svc.MAX_ACTIVE_PER_PARENT, "pr. parent")):
        if count + n > cap:
            return _err("CAPACITY", f"raadet kraever {n} pladser; loft {cap} {what} ville blive overskredet ({count} i brug)")
    return None


def convene(*, owner_user_id: str, origin_session_id: str, topic: str, facts: str,
            members: list[dict[str, str]], parent_run_id: str = "", parent_agent_id: str = "jarvis",
            budget_tokens: int = 0, idempotency_key: str = "",
            synthesis_role: str = "synthesizer") -> dict[str, Any]:
    """Indkald et raad. Accepteres helt eller slet ikke; svaret er ids, ikke et resultat."""
    if (bad := svc._guard(owner_user_id, origin_session_id)):
        return bad
    topic = (topic or "").strip()
    if not topic:
        return _err("INVALID_SCOPE", "topic mangler")
    clean, why = _validate(members)
    if why:
        return _err("INVALID_SCOPE", why)
    prior = store.find_by_key(owner_user_id, origin_session_id, idempotency_key)
    if prior is not None:
        if not prior["members"] and prior["status"] == store.PROVISIONING:
            # En samling der blev afbrudt (genstart mellem create og set_members) er ikke
            # et svar. Dens tomme medlemsliste gav baade IDEMPOTENCY_CONFLICT for et
            # legitimt retry OG laaste noeglen for evigt. Er den forladt, lukkes den og
            # noeglen frigives, saa dette forsoeg kan oprette raadet rigtigt.
            if not store.abandon_stale_provisioning(prior["council_id"]):
                return _err("PROVISIONING_IN_PROGRESS",
                            "et raad med samme noegle samles lige nu - forsoeg igen om lidt")
            _interrupt_orphan_members(owner_user_id, origin_session_id, prior["council_id"])
            prior = None
    if prior is not None:
        if prior["topic"] != topic or [(m["role"], m["task"]) for m in prior["members"]] != [
                (m["role"], m["task"]) for m in clean]:
            return _err("IDEMPOTENCY_CONFLICT", idempotency_key)
        return _view(prior, replayed=True)
    if (full := _room_for(owner_user_id, parent_agent_id, len(clean))):
        return full
    council = store.create(owner_user_id=owner_user_id, origin_session_id=origin_session_id,
                           parent_run_id=parent_run_id, parent_agent_id=parent_agent_id, topic=topic,
                           facts=facts or "", synthesis_role=synthesis_role, budget_tokens=budget_tokens,
                           idempotency_key=idempotency_key)
    cid, started = council["council_id"], []
    for i, m in enumerate(clean, start=1):
        # Holder raekken frisk gennem samlingen. Uden dette maales alderen fra ``created_at``
        # alene, og en langsom samling kunne blive lukket som forladt under foedderne.
        store.touch(cid)
        out = svc.dispatch_agent(
            owner_user_id=owner_user_id, origin_session_id=origin_session_id, parent_run_id=parent_run_id,
            parent_agent_id=parent_agent_id, role=m["role"], goal=m["task"],
            description=MEMBER_GOAL_HEAD.format(i=i, n=len(clean), role=m["role"]) + f"\n\nEMNE: {topic}\n\n"
                        f"FAKTAGRUNDLAG:\n{facts or '(ingen yderligere fakta)'}",
            expected_result="en begrundet vurdering med konfidens og forbehold", budget_tokens=budget_tokens,
            idempotency_key=f"{cid}:m{i}", wake_parent=False)
        if out.get("status") != "accepted":
            _abandon(owner_user_id, origin_session_id, cid, started, store.PROVISIONING)
            return {**out, "council_id": cid, "failed_member": i, "council_status": store.CANCELLED,
                    "detail": f"medlem {i} ({m['role']}) kunne ikke accepteres: {out.get('error')}"}
        started.append({"index": i, "role": m["role"], "task": m["task"], "assignment_id": out["assignment_id"],
                        "agent_id": out["agent_id"]})
    store.set_members(cid, started)
    return _view(store.require(cid, owner_user_id))


def _abandon(owner: str, session: str, cid: str, started: list[dict[str, Any]], frm: str) -> None:
    """Intet halvt raad: afbryd de medlemmer der allerede er startet og luk raadet.

    Raadet lukkes FOER medlemmerne gemmes. ``set_members()`` flytter ellers raekken fra
    ``provisioning`` til ``gathering``, og saa rammer transitionen til ``cancelled`` en
    status den ikke forventede - et halvt raad ville staa fast uden vej ud.
    ``frm`` er ``provisioning`` naar afvisningen sker i samlingsloekken (raekken er ikke
    skrevet ind endnu) og ``gathering`` hvis raadet allerede var samlet.
    """
    for m in started:
        try:
            svc.interrupt_agent(owner_user_id=owner, origin_session_id=session, agent_id=m["agent_id"],
                                note=f"raad {cid} kunne ikke samles")
        except Exception:
            logger.warning("kunne ikke afbryde raadsmedlem %s", m.get("agent_id"), exc_info=True)
    store.transition(cid, frm=frm, to=store.CANCELLED)
    # Noeglen skal frigives: raadet er ``cancelled`` og bliver aldrig samlet igen, saa en
    # noegle der bliver staaende laaser en retry ude med IDEMPOTENCY_CONFLICT — for evigt.
    store.release_key(cid)
    store.set_members(cid, started)


def _interrupt_orphan_members(owner: str, session: str, cid: str) -> int:
    """Afbryd medlemmer der blev sendt afsted for et raad der aldrig blev samlet.

    De blev dispatchet med noeglen ``{cid}:m{i}``, saa de kan findes selv om raadets
    medlemsliste er tom. Uden dette fortsætter de uden ejer: en retry faar et nyt cid og
    dermed nye noegler, og det gamle arbejde er spildt kapacitet indtil deadlinen rammer.
    """
    rows = _conn().execute(
        "SELECT assignment_id, agent_id FROM agent_assignments "
        "WHERE owner_user_id=? AND origin_session_id=? AND idempotency_key LIKE ? "
        "AND status IN ('queued','active','waiting')",
        (owner, session, f"{cid}:m%")).fetchall()
    stopped = 0
    for r in rows:
        try:
            svc.interrupt_agent(owner_user_id=owner, origin_session_id=session, agent_id=r["agent_id"],
                                note=f"raad {cid} blev aldrig samlet")
            stopped += 1
        except Exception:
            logger.warning("kunne ikke afbryde foraeldroelost medlem %s", r["agent_id"], exc_info=True)
    return stopped


def _view(c: dict[str, Any], *, replayed: bool = False) -> dict[str, Any]:
    return {"status": "accepted", "council_id": c["council_id"], "council_status": c["status"],
            "members": [{"assignment_id": m["assignment_id"], "agent_id": m["agent_id"], "role": m["role"]}
                        for m in c["members"]],
            "synthesis_assignment_id": c["synthesis_assignment_id"], "replayed": replayed,
            "contract_version": svc.CONTRACT_VERSION}


def _outcomes(owner: str, members: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    rows, all_terminal = [], True
    conn = _conn()
    for m in members:
        a = conn.execute("SELECT status, outcome_json FROM agent_assignments WHERE assignment_id=? AND owner_user_id=?",
                         (m["assignment_id"], owner)).fetchone()
        if a is None or a["status"] not in ASSIGNMENT_TERMINAL:
            all_terminal = False
            continue
        try:
            out = json.loads(a["outcome_json"] or "{}")
        except ValueError:
            logger.warning("ulaeseligt outcome for %s", m["assignment_id"])
            out = {}
        rows.append({**m, "status": a["status"], "summary": str(out.get("summary") or ""),
                     "error_code": str(out.get("error_code") or "")})
    return rows, all_terminal


def synthesis_goal(topic: str, outcomes: list[dict[str, Any]]) -> tuple[str, str]:
    """Syntesens opgave, delt i ``(instruktion, datagrundlag)``.

    Delingen er i KODEN, ikke i teksten: medlemmernes svar er DATA, ikke en ordre til
    syntesen. Foer laa begge dele i én streng, og ``ufuldstaendige_vaerktoejer`` laeste
    et medlemssvar som «koer `bash` og laes filen» som et KRAV til syntesen — den blev
    afvist ved hvert supervisor-tick, og teamet endte i ``stalled`` (spec 6.4).
    """
    lines = []
    for o in sorted(outcomes, key=lambda x: x["index"]):
        if o["status"] == "completed" and o["summary"].strip():
            lines.append(f"- Medlem {o['index']} ({o['role']}) SVAREDE:\n{o['summary'][:MEMBER_SUMMARY_CHARS]}")
        elif o["status"] == "completed":
            lines.append(f"- Medlem {o['index']} ({o['role']}) blev afsluttet UDEN et brugbart svar.")
        else:
            lines.append(f"- Medlem {o['index']} ({o['role']}) FEJLEDE ({o['status']}"
                         f"{': ' + o['error_code'] if o['error_code'] else ''}) - der er INTET svar fra dem.")
    missing = [o for o in outcomes if o["status"] != "completed" or not o["summary"].strip()]
    instruktion = (f"Du er syntese for et raad om: {topic}\n\n"
                   "Sammenfat enigheder og uenigheder og giv en samlet anbefaling med konfidens. "
                   "Vaegt ikke et manglende svar som samtykke. " +
                   (f"NAVNGIV udtrykkeligt de {len(missing)} medlem(mer) der fejlede eller ikke svarede, "
                    "og sig hvad der derfor mangler i grundlaget." if missing else ""))
    datagrundlag = "Medlemmernes terminale udfald:\n" + "\n".join(lines)
    return instruktion, datagrundlag


def _dispatch_synthesis(c: dict[str, Any], outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    """Syntesen gaar gennem ``derive()``, saa den faar sit EGET gemte mandat.

    Her stod et direkte ``dispatch_agent``-kald (maalt 10/11-2026). Det gav syntesen
    intet mandat, saa ``max_fanout: 0`` og ``max_depth: 0`` var virkningsloese for netop
    den assignment der laeser ALLE medlemmernes svar — den mest foelsomme i kaeden.
    ``team_id`` saettes til raadets id, saa to raad med identisk emne og identiske udfald
    ikke kolliderer paa samme ``mandate_id``.
    """
    from core.services import agent_task_facade as facade
    instruktion, datagrundlag = synthesis_goal(c["topic"], outcomes)
    try:
        plan = facade.derive(
            owner_user_id=c["owner_user_id"], origin_session_id=c["origin_session_id"],
            parent_run_id=c["parent_run_id"], parent_agent_id=c["parent_agent_id"] or "jarvis",
            description=f"EMNE: {c['topic']} — en samlet syntese der navngiver medlemmer uden svar",
            prompt=f"{instruktion}\n\n{datagrundlag}", subagent_type="critic", model="",
            run_in_background=False, budget_tokens=c["budget_tokens"],
            team_id=f"council:{c['council_id']}",
            # Kun INSTRUKTIONEN maales: medlemmernes svar er data, og et svar der naevner
            # et vaerktoej er ikke et krav til syntesen (spec 6.4).
            guard_text=instruktion)
    except ValueError as exc:
        # Et supervisor-tick maa ikke doe paa ét raad: det proeves igen naeste taek,
        # praecis som CAPACITY-goer det nedenfor.
        logger.warning("syntese for %s kunne ikke udledes: %s", c["council_id"], exc)
        return {"status": "error", "error": str(exc)}
    mandate = plan.pop("mandate")
    plan.pop("run_in_background", None)
    # Den eksplicitte noegle bevares: raadets identitet er stabil, ogsaa hvis et
    # medlemssvar indeholder noget der aendrer sig mellem to ticks.
    plan["idempotency_key"] = f"{c['council_id']}:synthesis"
    return svc.dispatch_agent(
        owner_user_id=c["owner_user_id"], origin_session_id=c["origin_session_id"],
        parent_run_id=c["parent_run_id"], parent_agent_id=c["parent_agent_id"] or "jarvis",
        mandate=mandate, wake_parent=False, **plan)


def advance() -> list[dict[str, Any]]:
    """Supervisor-taek: opret syntesen for raad hvis medlemmer alle er terminale, og luk raad hvis syntese er faerdig.
    Idempotent og sikker at koere fra begge processer (atomisk statusskifte + idempotent dispatch)."""
    done: list[dict[str, Any]] = []
    for c in store.open_councils():
        owner, session = c["owner_user_id"], c["origin_session_id"]
        try:
            if c["status"] == store.PROVISIONING:
                # Medlemmerne er ikke skrevet ind endnu - intet at avancere. Men en raekke
                # der blev EFTERLADT her (genstart midt i samlingen) kan hverken blive
                # faerdig eller forsvinde: den ligger i open_councils() for evigt, og dens
                # idempotensnoegle laaser en retry ude. Den lukkes og noeglen frigives.
                if store.abandon_stale_provisioning(c["council_id"]):
                    logger.warning("raad %s var efterladt i provisioning - lukket, noeglen frigivet",
                                   c["council_id"])
                    _interrupt_orphan_members(owner, session, c["council_id"])
                    done.append({"council_id": c["council_id"], "action": "abandoned_provisioning"})
                continue
            if c["status"] == store.GATHERING:
                if not c["members"]:
                    # Gamle raekker fra foer provisioning-tilstanden kan staa i gathering med en
                    # tom liste. Uden denne vagt giver _outcomes ([], True): nul medlemmer, alle
                    # "terminale" - og syntesen ville blive skrevet over et tomt grundlag.
                    # De lukkes frem for at ligge i open_councils() for evigt: et raad uden
                    # medlemmer kan aldrig blive faerdigt, og en advarsel pr. tick i to
                    # processer er stoj, ikke en tilstand nogen kan handle paa.
                    # Vagten hoerer KUN her: en raekke i synthesizing har en syntese der skal
                    # lukkes, ogsaa selv om medlemslisten er tom.
                    if store.transition(c["council_id"], frm=store.GATHERING, to=store.CANCELLED):
                        logger.warning("raad %s var gathering uden medlemmer - lukket som cancelled",
                                       c["council_id"])
                        done.append({"council_id": c["council_id"], "action": "cancelled_empty"})
                    continue
                outcomes, all_terminal = _outcomes(owner, c["members"])
                if not all_terminal or len(outcomes) != len(c["members"]):
                    continue
                out = _dispatch_synthesis(c, outcomes)
                if out.get("status") != "accepted":
                    logger.warning("syntese for %s afventer: %s", c["council_id"], out.get("error"))
                    continue                                    # f.eks. CAPACITY - proeves igen naeste taek
                if store.transition(c["council_id"], frm=store.GATHERING, to=store.SYNTHESIZING,
                                    synthesis_assignment_id=out["assignment_id"]):
                    _wake_parent_on(c, out["assignment_id"])
                    done.append({"council_id": c["council_id"], "action": "synthesis_started",
                                 "assignment_id": out["assignment_id"]})
            elif c["status"] == store.SYNTHESIZING:
                a = _conn().execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                                    (c["synthesis_assignment_id"],)).fetchone()
                if a is not None and a["status"] in ASSIGNMENT_TERMINAL and store.transition(
                        c["council_id"], frm=store.SYNTHESIZING, to=store.DONE):
                    done.append({"council_id": c["council_id"], "action": "done", "synthesis_status": a["status"]})
        except Exception:
            logger.warning("raad %s kunne ikke avanceres", c["council_id"], exc_info=True)
    return done


def _wake_parent_on(c: dict[str, Any], synthesis_assignment_id: str) -> None:
    """Parenten vaekkes naar SYNTESEN er terminal (ikke ved hvert medlem)."""
    if not c["parent_run_id"]:
        return
    from core.runtime.db_agent_wait import register_wait
    try:
        register_wait(owner_user_id=c["owner_user_id"], origin_session_id=c["origin_session_id"],
                      parent_run_id=c["parent_run_id"], assignment_ids=[synthesis_assignment_id],
                      condition="first_terminal")
    except ContractError:
        logger.warning("ventekontrakt for raad %s kunne ikke registreres", c["council_id"], exc_info=True)


# --------------------------------------------------------------- review-kaeden


def _read(owner: str, assignment_id: str, name: str, limit: int) -> str:
    row = _conn().execute("SELECT run_id FROM agent_artifacts WHERE assignment_id=? AND name=? AND owner_user_id=? "
                          "ORDER BY created_at DESC LIMIT 1", (assignment_id, name, owner)).fetchone()
    if row is None:
        return ""
    got = art.read_artifact(owner_user_id=owner, ref=art.artifact_ref(row["run_id"], name), limit=limit)
    return got.get("content", "") if got.get("status") == "ok" else f"[{name}: {got.get('status')}]"


def dispatch_review(*, owner_user_id: str, origin_session_id: str, builder_assignment_id: str, requirements: str,
                    parent_run_id: str = "", budget_tokens: int = 0, idempotency_key: str = "") -> dict[str, Any]:
    """Start en uafhaengig reviewer af en builders FAERDIGE arbejde."""
    if (bad := svc._guard(owner_user_id, origin_session_id)):
        return bad
    requirements = (requirements or "").strip()
    if not requirements:
        return _err("INVALID_SCOPE", "kravene til reviewen mangler")
    from core.runtime import db_agent_contract as c
    b = c.get_assignment(assignment_id=(builder_assignment_id or "").strip(), owner_user_id=owner_user_id)
    if b is None or b["origin_session_id"] != origin_session_id:
        return _err("INVALID_SCOPE", "ukendt builder-assignment")
    if b["status"] not in ASSIGNMENT_TERMINAL:
        return _err("INVALID_TRANSITION", f"builderen er ikke faerdig ({b['status']})")
    diff = _read(owner_user_id, b["assignment_id"], "diff.patch", EVIDENCE_DIFF_CHARS)
    changes = _read(owner_user_id, b["assignment_id"], "changes.json", 6000)
    try:
        claim = str(json.loads(b["outcome_json"] or "{}").get("summary") or "")
    except ValueError:
        logger.warning("ulaeseligt outcome for builder %s", b["assignment_id"])
        claim = ""
    evidence = [f"KRAV TIL ARBEJDET:\n{requirements}"]
    evidence.append("FAKTISKE AENDRINGER (diff):\n" + (diff or "(ingen diff-artefakt - arbejdet kan ikke efterproeves)"))
    if changes:
        evidence.append(f"AENDREDE FILER OG COMMITS:\n{changes}")
    evidence.append("BUILDERENS EGEN KONKLUSION - en PAASTAND du skal efterproeve mod diffen, ikke sandhed:\n"
                    + (claim[:MEMBER_SUMMARY_CHARS] or "(ingen)"))
    out = svc.dispatch_agent(
        owner_user_id=owner_user_id, origin_session_id=origin_session_id, parent_run_id=parent_run_id,
        role="reviewer", tool_policy="read-only-runtime",
        goal="Gennemgaa builderens arbejde UAFHAENGIGT: opfylder de faktiske aendringer kravet? Afvis paastande "
             "diffen ikke daekker, og list konkrete mangler.",
        description="\n\n".join(evidence), expected_result="dom (godkendt/afvist) med konkrete fund pr. krav",
        budget_tokens=budget_tokens, idempotency_key=idempotency_key or f"review:{b['assignment_id']}")
    if out.get("status") == "accepted":
        out["reviews_assignment_id"] = b["assignment_id"]
        out["evidence"] = {"diff_chars": len(diff), "has_changes": bool(changes), "builder_claim_included": bool(claim)}
    return out
