"""Bounded visible prompt for a member's own chat session.

The owner's visible prompt contains global continuity and private runtime
sections. Member conversations use their own workspace files and transcript
only; unknown identity or session ownership fails closed.
"""
from __future__ import annotations

from datetime import datetime, timezone

# Isoleringen blev tæt 8/10-2026 (commit 575f2771b, 18:42:10 +0200). Assistent-
# ture skrevet FØR den dato kan bære ejer-fakta der slap gennem shared/-fallbacken
# før fixet, og må ikke føres tilbage i en member-prompt. Bruger-ture er altid
# sikre — de er samtalepartnerens egne ord.
_MEMBER_TRANSCRIPT_CUTOFF = datetime(2026, 10, 8, 16, 42, 10, tzinfo=timezone.utc)


def _iso_dt(value) -> datetime | None:
    """ISO-tidsstempel fra chat_messages → aware datetime. None = ukendt."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:  # ugyldigt tidsstempel = ukendt alder; kalderen dropper turen (fail closed)
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def build_member_prompt(*, user_id: str, session_id: str, user_message: str = ""):
    from core.identity.session_access import arbejdsrum_for
    from core.identity.users import find_user_by_discord_id
    from core.runtime.workspace_paths import workspace_dir
    from core.services.chat_sessions import get_session_owner, recent_chat_session_messages
    from core.services.prompt_contract import PromptAssembly
    from core.services.secret_redaction import read_for_prompt, redact

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

    # Lærings-sløjfen (blok D, 9/10-2026): de `## Lært`-linjer konsolideringen har
    # skrevet til medlemmets EGEN USER.md — relevans-udvalgt for det de skriver nu.
    # Tom indtil skrivesiden har lagt noget der; headeren navngiver samtalepartneren,
    # så sektionen ikke lyver i en fremmeds prompt.
    try:
        from core.services.prompt_sections.learned_about_user import build_learned_section
        learned = build_learned_section(
            user_message,
            workspace_dir=root,
            header=f"Lært om {user.name} (relevant for det der skrives nu):",
        )
        if learned:
            sections.append(learned)
            included.append("USER.md (## Lært)")
    except Exception:  # lærings-sektionen er berigelse — en fejl må ikke koste prompten
        pass

    history = recent_chat_session_messages(session_id, limit=60)
    # Medlemmet ser HELE sin egen tråd; uden assistent-turene kan Jarvis ikke
    # følge en tråd eller referere til sit eget forrige svar. To værn holder
    # ejer-fakta ude: (1) assistent-ture fra før isolerings-fixet droppes —
    # ukendt tidsstempel droppes også (fail closed); (2) alt indhold maskeres
    # gennem secret_redaction, samme værn workspace-filerne får.
    transcript: list[dict[str, str]] = []
    for item in history:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "")
        if not content or role not in ("user", "assistant"):
            continue
        if role == "assistant":
            created = _iso_dt(item.get("created_at"))
            if created is None or created < _MEMBER_TRANSCRIPT_CUTOFF:
                continue
        transcript.append({"role": role, "content": redact(content)})
    return PromptAssembly(
        mode="visible_chat",
        text="\n\n".join(sections),
        included_files=included,
        conditional_files=[],
        derived_inputs=["member workspace and own session"],
        excluded_files=["shared owner state", "global continuity", "other sessions"],
        transcript_messages=transcript or None,
    )
