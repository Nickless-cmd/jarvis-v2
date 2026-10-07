"""De tre versionsmaerkede promptlag for en agentrequest + snapshot foer foerste modelkald (C3).

Spec: docs/specs/2026-10-07-agentorkestrering-og-subagenter.md (7).

1. fast delegationstekst (parent, stop- og rapporteringsregler) - ``agent-delegation-v1``
2. rolle-/persona-instruktion (agentens ``system_prompt`` + dens ``system_prompt_version``)
3. assignment: maal, forventet leverance, target, vaerktoejer, begraensninger, resultatformat

Den EFFEKTIVE tekst (efter redigering af hemmeligheder), versionerne, modelruten og
vaerktoejsskemaet gemmes i ``agent_run_prompts`` FOER det foerste modelkald, saa et run kan
revideres og genoptages forstaeligt. Prompten styrer arbejde; adgang afgoeres af policy ved
tool-dispatch - ingen prompt kan give ret ud over den.

Kun for kontrakt-bundne agenter (et aabent assignment); legacy-agenter beholder den gamle prompt.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

DELEGATION_VERSION = "agent-delegation-v1"
DELEGATION_TEXT = (
    "Du arbejder for Jarvis på assignment `{assignment_id}`. Brug kun de værktøjer og det "
    "target runtime har givet dig. Meddel blokering og usikkerhed; opfind ikke udført arbejde. "
    "Du kan sende en mellemrapport til din parent, men runtime sender også dit endelige udfald. "
    "Afslut med evidens, artefakter og det der mangler."
)
#: Afslutningsformat (§7): felterne angives efter relevans; manglende felter forbliver synlige.
RESULT_FIELDS = ("summary", "findings", "evidence", "changes", "tests", "uncertainty",
                 "blockers", "next_action")


def ensure_prompt_tables(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_run_prompts (
            run_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            delegation_version TEXT NOT NULL,
            role_version TEXT NOT NULL,
            layer_digests_json TEXT NOT NULL,
            effective_text TEXT NOT NULL,
            provider TEXT NOT NULL DEFAULT '',
            model TEXT NOT NULL DEFAULT '',
            tool_names_json TEXT NOT NULL DEFAULT '[]',
            tool_schema_sha256 TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _redact(text: str) -> str:
    try:
        from core.services.secret_redaction import redact
        return redact(text)
    except Exception:
        logger.warning("kunne ikke redigere hemmeligheder i agentprompt", exc_info=True)
        return text


def build_layered_prompt(*, agent: dict[str, Any], messages_text: str, execution_mode: str,
                         extra_instruction: str = "") -> dict[str, Any] | None:
    """Byg de tre lag, eller ``None`` for en agent uden aabent assignment (legacy-vejen)."""
    from core.runtime.db_agent_contract import open_assignment_for_agent

    a = open_assignment_for_agent(str(agent.get("agent_id") or ""))
    if a is None:
        return None
    try:
        context = json.loads(str(agent.get("context_json") or "{}"))
    except ValueError:
        context = {}
    # den fortrolige del af konteksten (identitet) hoerer ikke hjemme i barnets prompt
    context = {k: v for k, v in context.items() if k not in ("user_id", "parent_session_id")}
    try:
        tools = json.loads(str(agent.get("allowed_tools_json") or "[]"))
    except ValueError:
        tools = []
    layer1 = DELEGATION_TEXT.format(assignment_id=a["assignment_id"])
    layer2 = str(agent.get("system_prompt") or "")
    layer3 = "\n".join([
        f"Mål: {a['goal']}",
        f"Forventet leverance: {a['expected_result'] or '(ikke angivet)'}",
        f"Target: {a['target']}  |  Execution mode: {execution_mode}",
        f"Værktøjer: {', '.join(tools) if tools else '(ingen)'}  |  Politik: "
        f"{agent.get('tool_policy') or 'none'}",
        f"Resultatformat (efter relevans): {', '.join(RESULT_FIELDS)}",
        f"Kontekst: {json.dumps(context, ensure_ascii=False)}",
        "",
        f"Samtalen hidtil:\n{messages_text}",
        "",
        extra_instruction,
    ]).strip()
    role_version = str(agent.get("system_prompt_version") or "v1")
    text = _redact(
        f"[DELEGATION · {DELEGATION_VERSION}]\n{layer1}\n\n"
        f"[ROLLE · {agent.get('role') or 'agent'} · {role_version}]\n{layer2}\n\n"
        f"[OPGAVE · {a['assignment_id']}]\n{layer3}")
    return {"text": text, "assignment_id": a["assignment_id"], "owner_user_id": a["owner_user_id"],
            "delegation_version": DELEGATION_VERSION, "role_version": role_version,
            "digests": {"delegation": _sha(layer1), "role": _sha(layer2), "assignment": _sha(layer3)},
            "tool_names": list(tools)}


def snapshot_prompt(*, run_id: str, agent: dict[str, Any], layers: dict[str, Any],
                    tools_payload: list[dict] | None = None) -> bool:
    """Gem den effektive prompt + versioner + modelrute + vaerktoejsskema FOER foerste modelkald.
    Returnerer ``False`` (og logger) hvis det ikke kunne gemmes - runnet afbrydes ikke af det."""
    from core.runtime.db_agent_contract import _conn, _now_iso

    schema = json.dumps(tools_payload or [], sort_keys=True, ensure_ascii=False, default=str)
    names = [((t.get("function") or {}).get("name") or "") for t in (tools_payload or [])] \
        or list(layers.get("tool_names") or [])
    try:
        conn = _conn()
        conn.execute(
            "INSERT OR REPLACE INTO agent_run_prompts (run_id, assignment_id, agent_id, owner_user_id, "
            "delegation_version, role_version, layer_digests_json, effective_text, provider, model, "
            "tool_names_json, tool_schema_sha256, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, layers["assignment_id"], str(agent.get("agent_id") or ""), layers["owner_user_id"],
             layers["delegation_version"], layers["role_version"], json.dumps(layers["digests"]),
             layers["text"], str(agent.get("provider") or ""), str(agent.get("model") or ""),
             json.dumps(names), _sha(schema), _now_iso()))
        conn.commit()
        return True
    except Exception:
        logger.warning("promptsnapshot kunne ikke gemmes for %s", run_id, exc_info=True)
        return False


def get_prompt_snapshot(*, owner_user_id: str, run_id: str) -> dict[str, Any] | None:
    """Ejer-kontrolleret opslag; en andens run er ``None``."""
    from core.runtime.db_agent_contract import _conn, _row

    return _row(_conn().execute("SELECT * FROM agent_run_prompts WHERE run_id=? AND owner_user_id=?",
                                (run_id, owner_user_id)).fetchone())
