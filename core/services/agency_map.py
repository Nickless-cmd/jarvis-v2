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
    questions = _questions(bridges)
    counts = {
        "nodes": len(nodes),
        "bridges": len(bridges),
        "connected": sum(1 for item in bridges if item["status"] == "connected"),
        "partial": sum(1 for item in bridges if item["status"] == "partial"),
        "missing": sum(1 for item in bridges if item["status"] == "missing"),
        "experimental": sum(1 for item in bridges if item["status"] == "experimental"),
    }
    return {
        "fetchedAt": datetime.now(UTC).isoformat(),
        "mode": "living-agency-map",
        "summary": counts,
        "nodes": nodes,
        "bridges": bridges,
        "questions": questions,
        "nextMoves": [
            {
                "title": "Close tool-outcome memory",
                "summary": "Successful and failed tool runs should become durable executive evidence, not just events.",
                "target": "Tools -> Memory -> Living Executive",
                "priority": "high",
            },
            {
                "title": "Make Living Executive propose actions",
                "summary": "Executive traces are active now; the next step is candidate action proposals with MC-visible reasons.",
                "target": "Emotion/Goals -> Living Executive -> Tools",
                "priority": "high",
            },
            {
                "title": "Connect remembered patterns to choices",
                "summary": "Emotional anchors, concept baselines, and sensory memories should bias future executive choices.",
                "target": "Memory -> Choice",
                "priority": "medium",
            },
            {
                "title": "Expose dark edges in MC",
                "summary": "Any runtime signal that changes behavior but has no Mission Control surface should be listed here.",
                "target": "Hidden influence -> Mission Control",
                "priority": "medium",
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
        _bridge("living_executive", "memory", "partial", "Executive can write observations, but not all choices become durable lessons yet."),
        _bridge("memory", "living_executive", "partial", "Some memory signals influence executive choices; no general precedent engine yet."),
        _bridge("tools", "emotion", "partial", "Tool success/error concepts exist, but retry-success and nuanced outcomes are not mapped."),
        _bridge("tools", "memory", "missing", "Tool outcomes are not consistently converted into durable action evidence."),
        _bridge("living_executive", "tools", "partial", "Executive schedules wakeups and records focus, but does not yet propose full tool plans."),
        _bridge("mission_control", "living_executive", "connected", "MC exposes active state, current focus, recent traces, and allowed actions."),
        _bridge("hidden_runtime", "mission_control", "partial", "Many living signals are surfaced; hidden influence edges still need automatic inventory."),
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
            "answer": "Emotion and sensory novelty are active; full tool-plan proposal from those states is still partial.",
            "status": "partial",
        },
        {
            "question": "Hvad kan han handle på, men ikke huske?",
            "answer": "Tool outcomes and executive action outcomes need more durable memory/evidence rows.",
            "status": "open",
        },
        {
            "question": "Hvad kan han huske, men ikke bruge til valg?",
            "answer": "Sensory, emotional anchors, and concept baselines exist; a general precedent engine is not wired into all choices.",
            "status": "partial",
        },
        {
            "question": "Hvad sker i ham, men er stadig usynligt i MC?",
            "answer": f"{len(missing)} bridge(s) are still partial/missing; this tab is now the inventory surface.",
            "status": "active",
        },
    ]
