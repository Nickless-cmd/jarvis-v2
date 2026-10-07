"""Workspace path resolver — single source of truth for filesystem layout.

Replaces ~75 hardcoded `workspaces/default/` references across services.
Routes per-user requests to their workspace dir; routes Jarvis-state
requests to the shared dir.

Task 5 switched shared_dir() to `shared/` and renamed default → bjorn.

See: docs/superpowers/specs/2026-05-28-multi-user-workspace-isolation-design.md
"""
from __future__ import annotations

import os
from pathlib import Path


class NoUserContextError(RuntimeError):
    """Raised when workspace_dir() is called without a resolvable user_id.

    This is intentionally loud — we prefer a visible crash over a silent
    fallback to default/ that would leak the owner's data into a member's
    session.
    """


def _jarvis_home() -> Path:
    """JARVIS_HOME resolved at call time (so tests can override via env)."""
    return Path(os.environ.get("JARVIS_HOME") or os.path.expanduser("~/.jarvis-v2"))


def shared_dir() -> Path:
    """Jarvis' own state. All users see the same instance.

    Contains: SOUL.md, IDENTITY.md, MANIFEST.md, INNER_VOICE.md,
    CHRONICLE.md, dreams/, creative_impulse/, shadow_scan/, etc.
    """
    return _jarvis_home() / "shared"


def workspace_dir(user_id: str | None = None) -> Path:
    """Per-relation workspace. Defaults to current_user_id() from context.

    Contains: MEMORY.md, USER.md (per-relation state).

    Args:
        user_id: explicit discord_id. If None, reads from workspace_context.
                 If unresolvable → NoUserContextError (never silent default).

    Raises:
        NoUserContextError: when user_id is empty and no context is set,
                            or when user_id is not in users.json.
    """
    if not user_id:
        from core.identity.workspace_context import current_user_id
        user_id = current_user_id()
    if not user_id:
        raise NoUserContextError(
            "workspace_dir() called without user_id arg and no current_user_id() "
            "in context. Caller must either pass user_id= explicitly or be inside "
            "a user_context() / set_context() block."
        )
    workspace_name = _user_id_to_workspace_name(user_id)
    return _jarvis_home() / "workspaces" / workspace_name

def workspace_dir_or_owner() -> Path:
    """workspace_dir() with an owner fallback, then shared/ as last resort.

    For Jarvis' own entity-level reads (heartbeat, dreams, autonomous runs)
    there is no user context; his home is the owner's workspace — the same
    rule memory_tools._memory_md applies for writes (2026-07-22). Added
    2026-09-04 (memory repair, R5) so search paths never raise
    NoUserContextError in autonomous runs.
    """
    try:
        return workspace_dir()
    except NoUserContextError:
        pass
    try:
        from core.identity.users import get_owner
        owner = get_owner()
        owner_id = str(getattr(owner, "discord_id", "") or "").strip() if owner else ""
        if owner_id:
            return workspace_dir(owner_id)
    except Exception:
        pass
    return shared_dir()


def _user_id_to_workspace_name(user_id: str) -> str:
    """Resolve user_id → workspace folder name.

    Hybrid (users.json→SQLite-cutover): legacy users.json prøves FØRST (discord-id-
    brugere opfører sig 100% uændret — nul regression), SQLite users-tabellen som
    fallback (nyregistrerede brugere med user_id=UUID). Bevarer den LOUD
    NoUserContextError hvis ingen af dem kender brugeren (aldrig stille default →
    ingen data-lækage).
    """
    uid = str(user_id).strip()
    # 1) Legacy users.json (discord-id). Uændret adfærd for kendte brugere.
    try:
        from core.identity.users import find_user_by_discord_id
        user = find_user_by_discord_id(uid)
        if user is not None:
            return user.workspace
    except Exception:
        pass
    # 2) SQLite users-tabel (user_id = UUID). Nyregistrerede selvbetjenings-brugere.
    try:
        from core.runtime.db_users import get_user_row
        row = get_user_row(uid)
        if row and not row.get("deleted_at"):
            ws = str(row.get("workspace") or "").strip()
            if ws:
                return ws
    except Exception:
        pass
    raise NoUserContextError(
        f"user_id={user_id!r} ikke fundet i users.json eller SQLite-tabellen — "
        "nægter at defaulte til 'default'-workspace (ville lække owner-data). "
        "Registrér brugeren (scripts/users_cli.py add eller register_user), eller "
        "pass et eksplicit user_id."
    )


def rent_mappe_eller_filnavn(navn: str) -> str:
    """Et BLOT navn — ingen sti, ingen `..`. Tom streng når det ikke er det.

    `Path(x).name` alene er IKKE nok, og det er den fælde der gør funktionen
    nødvendig. Målt 4/10-2026:

        Path("..").name == ".."      → en navne-lighed slipper `..` igennem
        Path(".").name  == ""        → men `.` falder

    En rute der kun sammenlignede med `.name` lod altså `ws=..` passere og
    slog op i `files/u/../<fil>` — altså den gamle fælles mappe. Min egen
    isolations-test fandt det; tjekket havde set rigtigt ud.

    Derfor ét sted. Ruten, signeringen, værktøjet og migreringen spurgte før
    hver for sig, og fire kopier af en sikkerhedsregel driver fra hinanden.
    """
    rent = str(navn or "").strip()
    if not rent or rent in (".", "..") or rent != Path(rent).name:
        return ""
    return rent


def published_files_dir(user_id: str | None = None, *, opret: bool = False) -> Path:
    """Hvor ÉN brugers udgivne filer bor. `~/.jarvis-v2/files/u/<workspace>/`.

    ## Hvorfor den findes (Bjørn 4/10-2026: «filer skal være per bruger»)

    Indtil nu lå alt i én flad `files/`-mappe: målt samme dag 151 filer, som
    enhver autentificeret husstandsbruger kunne hente med sit eget token.
    `GET /files/{navn}` slog op direkte i mappen uden at spørge hvem der
    spurgte. De andres workspaces er krypterede netop for at folk ikke kan
    læse hinandens ting; udgivne filer var et hul i den linje.

    ## Hvorfor `files/u/` og ikke `files/<workspace>/`

    `files/` har allerede syv undermapper fra eksperimenter — `phase5`,
    `phase6`, `phase7`, `phase7b`, `icons`, `latency`, `tts-samples`. Et
    workspace der en dag kom til at hedde det samme ville smelte sammen med
    en af dem. `u/` gør navnerummet entydigt, og det koster én sti-del.

    ## Hvorfor IKKE inde i selve workspacet

    `workspaces/<navn>/` er det oplagte sted, og det er forkert her:
    `workspace_crypto` krypterer workspace-filer når
    `JARVISX_ENCRYPT_WORKSPACES=1` (målt 4/10: slået fra i dag). Blev den
    slået til, ville en udgiven PDF blive krypteret på skrivning og serveret
    som kryptotekst. Afgrænsningen her er en sti-regel, ikke en fil-form.

    Rejser `NoUserContextError` når brugeren ikke kan afgøres — med vilje, og
    af samme grund som `workspace_dir`: et tavst fald til en fælles mappe er
    præcis den lækage denne funktion lukker.
    """
    navn = _user_id_to_workspace_name(user_id or "") if user_id else None
    if navn is None:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id()
        if not uid:
            raise NoUserContextError(
                "published_files_dir() uden user_id og uden current_user_id(). "
                "Kalderen skal enten sende user_id= eller koere inde i en "
                "user_context()/set_context()-blok."
            )
        navn = _user_id_to_workspace_name(uid)
    sti = _jarvis_home() / "files" / "u" / navn
    if opret:
        sti.mkdir(parents=True, exist_ok=True)
    return sti


def published_file_path(filnavn: str, user_id: str | None = None,
                        *, opret_mappe: bool = False) -> Path:
    """Den fulde sti til ÉN brugers fil. Rejser ValueError på en sti.

    `Path(x).name` ÉT sted, så kalderen ikke kan have sin egen mening om hvad
    der er et filnavn. Tre steder ville før have hver sin rensning — ruten,
    værktøjet og signeringen — og den slags driver fra hinanden.
    """
    rent = rent_mappe_eller_filnavn(Path(str(filnavn or "").strip()).name)
    if not rent:
        raise ValueError(f"ugyldigt filnavn: {filnavn!r}")
    return published_files_dir(user_id, opret=opret_mappe) / rent
