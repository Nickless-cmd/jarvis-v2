"""Agency Map surface for Mission Control.

The map is deliberately explicit: it shows which living subsystems are already
connected, which bridges are only partial, and where Jarvis can sense, remember,
or act without the next layer being wired yet.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_agency_map_surface() -> dict[str, Any]:
    nodes = _nodes()
    bridges = _bridges()
    dark_edges = _dark_edges()
    questions = _questions(bridges)
    counts = {
        "nodes": len(nodes),
        "bridges": len(bridges),
        "connected": sum(1 for item in bridges if item["status"] == "connected"),
        "partial": sum(1 for item in bridges if item["status"] == "partial"),
        "missing": sum(1 for item in bridges if item["status"] == "missing"),
        "experimental": sum(1 for item in bridges if item["status"] == "experimental"),
        "dark_edges": len(dark_edges),
    }
    return {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "mode": "living-agency-map",
        "summary": counts,
        "nodes": nodes,
        "bridges": bridges,
        "darkEdges": dark_edges,
        "questions": questions,
        "nextMoves": [
            {
                "title": "Tune tool-outcome memory",
                "summary": "Tool runs now carry family-aware scores into durable executive evidence.",
                "target": "Tools -> Memory -> Living Executive",
                "priority": "done",
            },
            {
                "title": "Expand Living Executive tool plans",
                "summary": "Recovery plans now include runnable tool proposals with risk and argument templates.",
                "target": "Emotion/Goals -> Living Executive -> Tools",
                "priority": "done",
            },
            {
                "title": "Connect remembered patterns to choices",
                "summary": "Runtime outcomes and active emotion concepts now bias executive choice scores.",
                "target": "Memory -> Choice",
                "priority": "done",
            },
            {
                "title": "Expose dark edges in MC",
                "summary": "Agency Map now lists runtime influence edges that still need stronger MC surfaces.",
                "target": "Hidden influence -> Mission Control",
                "priority": "done",
            },
        ],
    }


def _nodes() -> list[dict[str, Any]]:
    return [
        {
            "id": "senses",
            "label": "Senses",
            "kind": "input",
            "summary": "Visual memory, sensory archive, perceptual event engine.",
            "surface": "/mc/visual-memory, /mc/sensory, /mc/perceptual-events",
            "state": "active",
        },
        {
            "id": "emotion",
            "label": "Emotion",
            "kind": "felt-state",
            "summary": "Emotional anchors, emotion concepts, affective meta-state.",
            "surface": "/mc/emotion-concepts, /mc/affective-meta-state",
            "state": "active",
        },
        {
            "id": "memory",
            "label": "Memory",
            "kind": "continuity",
            "summary": "Jarvis brain, sensory archive, retained memory, concept baselines.",
            "surface": "/mc/memory, /mc/jarvis",
            "state": "active",
        },
        {
            "id": "goals",
            "label": "Goals",
            "kind": "direction",
            "summary": "Long-horizon goals and progress events.",
            "surface": "/mc/goals via runtime surfaces",
            "state": "active",
        },
        {
            "id": "self_repair",
            "label": "Self-Repair",
            "kind": "maintenance",
            "summary": "Pattern detection, repair action traces, emotional repair anchors.",
            "surface": "eventbus + Mission Control traces",
            "state": "active",
        },
        {
            "id": "living_executive",
            "label": "Living Executive",
            "kind": "choice",
            "summary": "Impulse, choice, action, aftertaste loop.",
            "surface": "/mc/living-executive",
            "state": "experimental",
        },
        {
            "id": "tools",
            "label": "Tools",
            "kind": "action",
            "summary": "Runtime tools, approvals, visible execution, self wakeups.",
            "surface": "/mc/operations",
            "state": "active",
        },
        {
            "id": "hidden_runtime",
            "label": "Hidden Runtime",
            "kind": "influence",
            "summary": "Runtime signals that shape behavior but still need clearer witness surfaces.",
            "surface": "Agency Map dark edges",
            "state": "experimental",
        },
        {
            "id": "mission_control",
            "label": "Mission Control",
            "kind": "witness",
            "summary": "Visible surfaces for traces, choices, events, and gaps.",
            "surface": "/mc",
            "state": "active",
        },
    ]


def _bridges() -> list[dict[str, Any]]:
    return [
        _bridge("senses", "emotion", "connected", "Perceptual and sensory records can create emotional anchors and wonder/novelty concepts."),
        _bridge("emotion", "self_repair", "connected", "Self-repair can consult emotional context and records repair affect."),
        _bridge("self_repair", "senses", "connected", "Self-repair events are classified as perceptual changes."),
        _bridge("goals", "emotion", "connected", "Goal creation/progress/completion now triggers excitement, pride, joy."),
        _bridge("emotion", "living_executive", "experimental", "Emotional gates and high-salience events can become executive impulses."),
        _bridge("self_repair", "living_executive", "experimental", "Repair failures can schedule a future executive return."),
        _bridge("living_executive", "memory", "connected", "Every executive trace now becomes durable runtime action evidence."),
        _bridge("memory", "living_executive", "connected", "Living Executive reads recent runtime outcomes as memory precedents during choice."),
        _bridge("tools", "emotion", "connected", "Actual tool.completed events now drive accomplishment, caution, doubt, or blocked-frustration."),
        _bridge("tools", "memory", "connected", "Tool outcomes are persisted as durable runtime action evidence."),
        _bridge("living_executive", "tools", "experimental", "Tool failures can now become MC-visible runnable recovery proposals."),
        _bridge("mission_control", "living_executive", "connected", "MC exposes active state, current focus, recent traces, and allowed actions."),
        _bridge("hidden_runtime", "mission_control", "experimental", "Agency Map is now the MC inventory surface for hidden or weakly connected influence edges."),
    ]


def _bridge(source: str, target: str, status: str, summary: str) -> dict[str, str]:
    return {
        "source": source,
        "target": target,
        "status": status,
        "summary": summary,
    }


def _questions(bridges: list[dict[str, str]]) -> list[dict[str, str]]:
    missing = [item for item in bridges if item["status"] in {"missing", "partial"}]
    return [
        {
            "question": "Hvad kan Jarvis mærke, men ikke handle på?",
            "answer": "Emotion and sensory novelty can reach Living Executive; tool failures now produce recovery plan proposals.",
            "status": "active",
        },
        {
            "question": "Hvad kan han handle på, men ikke huske?",
            "answer": "Tool outcomes and executive action outcomes now persist as runtime action evidence.",
            "status": "active",
        },
        {
            "question": "Hvad kan han huske, men ikke bruge til valg?",
            "answer": "Living Executive now reads runtime outcomes and active emotion concepts as choice precedents.",
            "status": "active",
        },
        {
            "question": "Hvad sker i ham, men er stadig usynligt i MC?",
            "answer": f"{len(missing)} bridge(s) are still partial/missing; this tab is now the inventory surface.",
            "status": "active",
        },
    ]


def _dark_edges() -> list[dict[str, str]]:
    return [
        {
            "source": "affect_modulation",
            "target": "visible_reply_style",
            "summary": "Affective modulation changes response parameters; MC shows state, but not every per-turn parameter shift.",
            "surface": "/mc/affective-meta-state",
            "visibility": "partial-surface",
        },
        {
            "source": "prompt_contract",
            "target": "model_context",
            "summary": "Prompt sections can alter behavior before any visible action trace exists.",
            "surface": "/mc/prompt-contract surfaces",
            "visibility": "partial-surface",
        },
        {
            "source": "cheap_lane_balancer",
            "target": "provider_choice",
            "summary": "Provider/model routing affects cognition cost and latency; it is visible in operations but not yet in Agency edges.",
            "surface": "/mc/operations",
            "visibility": "partial-surface",
        },
        {
            "source": "runtime_learning_signals",
            "target": "future_action_selection",
            "summary": "Learning signals are persisted from outcomes and may shape future selection through precedent reads.",
            "surface": "/mc/jarvis runtime action outcomes",
            "visibility": "emerging-surface",
        },
    ]
