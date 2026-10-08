"""Bounded visible prompt for a member's own chat session.

The owner's visible prompt contains global continuity and private runtime
sections. Member conversations use their own workspace files and transcript
only; unknown identity or session ownership fails closed.
"""
from __future__ import annotations


def build_member_prompt(*, user_id: str, session_id: str):
    from core.identity.session_access import arbejdsrum_for
    from core.identity.users import find_user_by_discord_id
    from core.runtime.workspace_paths import workspace_dir
    from core.services.chat_sessions import get_session_owner, recent_chat_session_messages
    from core.services.prompt_contract import PromptAssembly
    from core.services.secret_redaction import read_for_prompt

    user = find_user_by_discord_id(user_id)
    if user is None or user.role == "owner" or not user.workspace:
        raise PermissionError("Member prompt requires a known non-owner")
    owner_id = get_session_owner(session_id)
    if not owner_id or arbejdsrum_for(owner_id) != user.workspace:
        raise PermissionError("Member prompt requires the user's own session")

    root = workspace_dir(user_id)
    sections = [
        "Du er Jarvis. Din nuværende samtalepartner er " + user.name + ". "
        "Når brugeren siger 'jeg' eller spørger 'hvad ved du om mig', handler det "
        "om denne samtalepartner. Brug kun denne brugers workspace og samtale "
        "som personlige kilder. Hvis du ikke ved noget om brugeren, sig det. "
        "Del aldrig en anden brugers private oplysninger."
    ]
    included: list[str] = []
    for filename in ("SOUL.md", "IDENTITY.md", "USER.md", "MEMORY.md"):
        # Direct member path: never resolve a short file to shared/ owner state.
        content = read_for_prompt(root / filename)
        if content:
            sections.append(f"{filename} (kun {user.name}s workspace):\n{content[:6000]}")
            included.append(filename)

    history = recent_chat_session_messages(session_id, limit=60)
    # Older assistant turns may themselves contain owner facts leaked before
    # this fix. Do not feed those answers back into a new member prompt.
    transcript = [
        {"role": str(item["role"]), "content": str(item.get("content") or "")}
        for item in history
        if item.get("role") == "user" and item.get("content")
    ]
    return PromptAssembly(
        mode="visible_chat",
        text="\n\n".join(sections),
        included_files=included,
        conditional_files=[],
        derived_inputs=["member workspace and own session"],
        excluded_files=["shared owner state", "global continuity", "other sessions"],
        transcript_messages=transcript or None,
    )
