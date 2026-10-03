"""Trusted-folder gate for code/cowork workspaces.

Claude Desktop-mønster: et workspace er læsbart med det samme, men skrive- og
exec-værktøjer (write_file/edit_file/bash + operator-modparter) blokeres indtil
brugeren eksplicit har markeret mappen som *betroet*. Trust er vedvarende pr.
(user_id, kind, root) og lever i sin egen tabel — ingen db.py-ændring.

Håndhævelse sker centralt i ``simple_tools.execute_tool`` via ``guard_code_write``,
som læser en request-scopet ContextVar sat i ``visible_runs._stream_visible_run``.
"""
from __future__ import annotations

import contextvars
from datetime import UTC, datetime

from core.runtime.db import connect

# Skrive-/exec-værktøjer der kræver betroet workspace i code-scope.
_CODE_WRITE_TOOLS = frozenset({
    "write_file", "edit_file", "bash",
    "operator_write_file", "operator_edit_file", "operator_bash",
})

# Request-scopet trust-kontekst: {"kind","root","trusted"} sat ved run-entry.
_trust_ctx: contextvars.ContextVar[dict] = contextvars.ContextVar(
    "jarvis_ws_trust", default={},
)


def _ensure_table(conn) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_trust (
            user_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            root TEXT NOT NULL,
            trusted_at TEXT NOT NULL,
            PRIMARY KEY (user_id, kind, root)
        )
        """
    )


def _opløst(sti: str) -> str:
    """Stien med symlinks fulgt — tom streng hvis den ikke kan opløses.

    `realpath` er hele sikkerheden i arven nedenfor: en symlink INDE i en
    betroet mappe, der peger på `/etc`, har en sti der ser ud som om den ligger
    under roden, men opløses til `/etc` og falder dermed udenfor. Uden
    opløsningen ville en ren streng-sammenligning gøre enhver betroet mappe til
    en vej ud af sandkassen.
    """
    try:
        import os.path
        s = str(sti or "").strip()
        if not s:
            return ""
        return os.path.realpath(os.path.expanduser(s))
    except Exception:  # kan stien ikke oploeses, arver den INGEN tillid. Fail
        # mod det lukkede: en sti vi ikke kan afgoere maa ikke blive betroet.
        return ""


def er_under(sti: str | None, rod: str | None) -> bool:
    """Ligger `sti` i eller under `rod`?

    Grænsen tjekkes på mappe-niveau, ikke som præfiks: `/media/x-ondsindet` må
    ikke matche `/media/x`, og det ville en bar `startswith` sige ja til.

    ABSOLUTTE stier (workstation-scope) opløses med `realpath`, så en symlink
    ud af roden ikke følger med. RELATIVE stier (container-scope) er logiske
    navne inde i repoet — de normaliseres kun, for `realpath` på en relativ sti
    afhænger af processens arbejdsmappe, og det må en tillids-afgørelse ikke.

    Blandede former sammenlignes ikke: uden en fælles rod er svaret et gæt, og
    et gæt om tillid skal være NEJ.
    """
    import os.path
    a = str(sti or "").strip()
    b = str(rod or "").strip()
    if not a or not b:
        return False
    a_abs, b_abs = os.path.isabs(os.path.expanduser(a)), os.path.isabs(os.path.expanduser(b))
    if a_abs != b_abs:
        return False
    if a_abs:
        barn, foraelder = _opløst(a), _opløst(b)
    else:
        barn, foraelder = os.path.normpath(a), os.path.normpath(b)
    if not barn or not foraelder:
        return False
    # «.» ville ellers aegte enhver relativ sti som sit barn.
    if foraelder in (".", ""):
        return False
    if barn == foraelder:
        return True
    return barn.startswith(foraelder.rstrip(os.sep) + os.sep)


def is_trusted(user_id: str | None, kind: str | None, root: str | None) -> bool:
    """True hvis (user_id, kind, root) er betroet — direkte ELLER som undermappe.

    ## Arven (3/10-2026)

    Bjørn: «det først melder desk trusted folder fejl». Målt: `is_trusted`
    krævede et NØJAGTIGT match på `root`, så en side-opgave der startede i sin
    egen git-worktree under repoet — `.worktrees/side-fix-…` — blev afvist,
    selvom repo-roden var betroet. Mappen fandtes ikke da han trykkede tillid
    på repoet, og den kan ikke findes på forhånd, fordi navnet dannes af
    opgavens titel.

    En betroet mappe betyder «jeg stoler på hvad der ligger her» — og det
    inkluderer de mapper værktøjerne selv opretter under den. Samme regel som
    en editor der åbner et projekt: du betror projektet, ikke hver undermappe.

    Opløsningen i `er_under` er grænsen: en symlink ud af roden følger IKKE
    med, så arven kan ikke bruges til at nå uden for det betroede træ.
    """
    if not kind or not root:
        return False
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            "SELECT 1 FROM workspace_trust WHERE user_id = ? AND kind = ? AND root = ?",
            (user_id or "", kind, root),
        ).fetchone()
        if row is not None:
            return True
        # Arven: er den under en mappe brugeren HAR betroet i samme scope?
        betroede = conn.execute(
            "SELECT root FROM workspace_trust WHERE user_id = ? AND kind = ?",
            (user_id or "", kind),
        ).fetchall()
    return any(er_under(root, str(r[0])) for r in betroede)


def list_trusted(user_id: str | None, kind: str | None = None) -> list[dict[str, str]]:
    """De mapper brugeren har betroet — nyeste foerst.

    Tabellen har baaret svaret hele tiden; der var bare ingen der kunne spoerge
    om det. `is_trusted` svarer paa én mappe ad gangen, saa en vaelger maatte
    kende kandidaterne paa forhaand — og dermed kunne den ikke bygges.

    `kind` filtrerer paa container/workstation. Uden filter kommer begge, saa
    kalderen kan vise dem hver for sig uden to kald.
    """
    with connect() as conn:
        _ensure_table(conn)
        if kind:
            raekker = conn.execute(
                "SELECT kind, root, trusted_at FROM workspace_trust "
                "WHERE user_id = ? AND kind = ? ORDER BY trusted_at DESC",
                (user_id or "", kind),
            ).fetchall()
        else:
            raekker = conn.execute(
                "SELECT kind, root, trusted_at FROM workspace_trust "
                "WHERE user_id = ? ORDER BY trusted_at DESC",
                (user_id or "",),
            ).fetchall()
    return [
        {"kind": str(r[0]), "root": str(r[1]), "trusted_at": str(r[2])}
        for r in raekker
    ]


def set_trusted(
    user_id: str | None, kind: str, root: str, trusted: bool,
) -> bool:
    """Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand."""
    with connect() as conn:
        _ensure_table(conn)
        if trusted:
            conn.execute(
                "INSERT OR REPLACE INTO workspace_trust(user_id, kind, root, trusted_at) "
                "VALUES (?, ?, ?, ?)",
                (user_id or "", kind, root, datetime.now(UTC).isoformat()),
            )
        else:
            conn.execute(
                "DELETE FROM workspace_trust WHERE user_id = ? AND kind = ? AND root = ?",
                (user_id or "", kind, root),
            )
        conn.commit()
    return trusted


# --- Request-scopet kontekst (sættes i visible_runs, læses i execute_tool) ---

def set_trust_context(*, kind: str | None, root: str | None, trusted: bool) -> None:
    _trust_ctx.set({"kind": kind or "", "root": root or "", "trusted": bool(trusted)})


def clear_trust_context() -> None:
    _trust_ctx.set({})


def current_trust_context() -> dict:
    return _trust_ctx.get()


def guard_code_write(tool_name: str) -> str | None:
    """Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et
    ikke-betroet code-workspace; ellers None (tilladt)."""
    if tool_name not in _CODE_WRITE_TOOLS:
        return None
    ctx = _trust_ctx.get()
    # Kun håndhæv når vi faktisk er i et code-workspace med en binding.
    if not ctx or not ctx.get("kind") or not ctx.get("root"):
        return None
    if ctx.get("trusted"):
        return None
    return (
        f"Workspace '{ctx.get('root')}' er ikke betroet. Jarvis kan læse her, "
        f"men skrive- og exec-handlinger ({tool_name}) kræver at brugeren først "
        f"markerer mappen som betroet i Code-fladen."
    )
