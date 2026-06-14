from core.tools.agent_dispatch_tool.tool import _exec_dispatch_code_mode_task

AGENT_DISPATCH_TOOL_DEFINITIONS = [
    {
        "name": "dispatch_code_mode_task",
        "description": (
            "Orchestrate a coding task across a team of internal agents (§19). "
            "Runs a skill-safety scan, decides inline-vs-dispatch, plans roles, "
            "and (when execute=true) spawns budget-limited agents that work in "
            "parallel. Default execute=false returns the plan without spawning "
            "(side-effect free). Use for multi-step tasks worth parallelizing; "
            "for a single scoped code edit prefer dispatch_to_claude_code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "What to accomplish."},
                "inline": {"type": "boolean", "description": "Force inline (true) or dispatch (false); omit to let the heuristic decide."},
                "executor_count": {"type": "integer", "description": "How many executor agents (1-4)."},
                "execute": {"type": "boolean", "description": "true = actually spawn agents; false (default) = plan only."},
            },
            "required": ["task"],
        },
    },
]

__all__ = [
    "_exec_dispatch_code_mode_task",
    "AGENT_DISPATCH_TOOL_DEFINITIONS",
]
