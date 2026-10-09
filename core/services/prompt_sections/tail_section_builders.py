"""Smaa, selvstaendige sektionsbyggere til promptens dynamiske hale.

Boy Scout-udskillelse (2026-10-07) fra ``core/services/prompt_contract.py`` (4.833 linjer): den naermeste
sammenhaengende gruppe ved tilfoejelsen af agenttilstanden i halen (G5) - de per-tur-sektioner der hver bygger
en kort tekst (eller ``None``) uden at dele tilstand med resten af assemblyen: Central-notices, aabne loefter,
forbundne apps, aabne spoergsmaal og tids-pinen. Koden er uaendret; ``prompt_contract`` re-eksporterer navnene,
saa kaldere og tests der importerer dem derfra virker som foer.
"""
from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


def _central_notices_section() -> str | None:
    """Medium-niveau Central-notices til Jarvis (spec 2026-06-23 §2). IKKE severe (dem
    ntfy'er Centralen), IKKE low (dem er trace-only). Kompakt: max 3, max 1 pr. nerve.
    Returnerer None (tom sektion) når ingen notices → brænder 0 tokens. Selv-sikker."""
    try:
        from core.runtime.db_central_incidents import list_central_incidents
        incidents = list_central_incidents(unresolved_only=True, limit=40)
        medium = [
            i for i in incidents
            if str(i.get("severity")) == "error"        # ikke "severe"
            and str(i.get("kind")) != "fail_open"        # ikke sikkerhed
        ]
        if not medium:
            return None
        seen: set[str] = set()
        lines: list[str] = []
        for i in medium[:12]:
            nerve = f"{i.get('cluster')}/{i.get('nerve')}"
            if nerve in seen:
                continue
            seen.add(nerve)
            lines.append(f"  • {nerve}: {str(i.get('message') or '')[:80]}")
            if len(lines) >= 3:
                break
        if not lines:
            return None
        return "[CENTRAL-NOTICE] medium:\n" + "\n".join(lines)
    except Exception:
        return None  # selv-sikker: crash = tom sektion, ikke crashet prompt


def _pending_promises_section(session_id: str | None) -> str | None:
    """Bjørn-gate (16. jun 2026): rejs Jarvis' åbne fremtids-løfter prominent, så
    han konfronteres med dem NÆSTE tur i stedet for at glide. None hvis ingen.

    Det manglende ansvarligheds-stykke i lie-crisis'en: unfinished_intent fanger
    løftet i selve turen, men intet holdt ham ansvarlig på tværs af ture. Læser
    `promise_ledger.pending_promises`. Placeres øverst i den DYNAMISKE assembly."""
    sid = (session_id or "").strip()
    if not sid:
        return None
    try:
        from core.services.promise_ledger import pending_promises
        pend = pending_promises(sid)
    except Exception:
        # Løfte-værnet må ikke forsvinde TAVST. Sektionen udelades (prompten skal
        # kunne bygges), men fejlen skal kunne ses: et ledger-fejl betyder at
        # Jarvis ikke konfronteres med sine uindfriede løfter den tur.
        # (Målt 9/10-2026: dette fald var ét af 24 tavse i prompt_sections.)
        LOGGER.warning("_pending_promises_section: kunne ikke læse løfter - udelades", exc_info=True)
        return None
    if not pend:
        return None
    lines = [f'- "{str(p.get("text", "")).strip()}"' for p in pend[-3:] if p.get("text")]
    if not lines:
        return None
    return (
        "⚠️ ÅBNE LØFTER (Bjørn-gate) — i de seneste ture sagde du at du ville gøre "
        "følgende. FØR du svarer noget andet: har du FAKTISK gjort det med værktøjer "
        "i denne tur? Hvis ja, vis beviset (commit-hash fra git log, test-output). "
        "Hvis nej, så GØR det nu — eller sig ærligt og kort at du ikke har gjort det "
        "endnu. Ingen flere 'jeg gør det'-løfter uden handling:\n" + "\n".join(lines)
    )


def _connected_connectors_section() -> str | None:
    """Surface brugerens FORBUNDNE plugins/connectors så Jarvis ved han har adgang.

    Bjørn 17. jun: "vi skal være sikre på at de apps der er connectet faktisk vises
    for ham så han ved han har adgang og hvordan han skal bruge dem." Læser
    connectors.list_for_user(current_user_id) og lister kun OAuth-connectors der er
    BÅDE connected OG enabled (de lokale som computer-use kender han allerede via tools).
    """
    try:
        from core.identity.workspace_context import current_user_id
        from core.services.connectors import list_for_user
        uid = (current_user_id() or "").strip()
        if not uid:
            return None
        items = list_for_user(uid)
    except Exception:
        # Uden dette ser Jarvis ikke sine forbundne apps og kan tro han ikke har
        # adgang. Sektionen udelades, men fejlen skal kunne ses.
        LOGGER.warning("_connected_connectors_section: kunne ikke læse connectors - udelades", exc_info=True)
        return None
    # Per-connector "sådan bruger du den"-hint (tool-navne). Udvid efterhånden.
    _HINTS = {
        "github": "kald github_list_issues(repo='ejer/navn') eller github_list_prs(repo=…)",
        "gmail": "kald gmail_search(query='is:unread') eller gmail_list() — brugerens egen indbakke",
        "google-calendar": "kald calendar_list_events() — brugerens kommende aftaler",
        "google-drive": "kald drive_search(query=…) — brugerens egne Drive-filer",
        "google-docs": "kald docs_read(document_id=…) — læs et Google-dokument",
        "google-sheets": "kald sheets_read(spreadsheet_id=…, range='Ark1!A1:D20')",
        "google-slides": "kald slides_read(presentation_id=…)",
    }
    lines: list[str] = []
    for c in items:
        if c.get("kind") != "oauth":
            continue
        if not (c.get("connected") and c.get("enabled")):
            continue
        hint = _HINTS.get(str(c.get("id") or ""))
        name = str(c.get("name") or c.get("id") or "")
        lines.append(f"- {name}: forbundet" + (f" — {hint}" if hint else ""))
    if not lines:
        return None
    return (
        "🔌 FORBUNDNE APPS (plugins) — brugeren har forbundet disse i Marketplace, og "
        "du HAR adgang til dem lige nu via dine værktøjer. Brug dem når det er relevant "
        "i stedet for at sige at du ikke kan:\n" + "\n".join(lines)
    )


def _open_questions_section(*, limit: int = 5) -> str | None:
    """Surface curiosity_daemon._open_questions into the visible prompt.

    The daemon collects questions Jarvis wondered about but didn't pursue
    (gaps in thoughts, "ved ikke", "..."). Without surfacing them they die
    in the buffer. Showing the recent N gives the model a chance to bring
    one up if it's relevant to the current turn.
    """
    try:
        from core.services.curiosity_daemon import _open_questions
        questions = list(_open_questions)[:limit]
    except Exception:
        # Åbne spørgsmål dør i bufferen hvis de ikke overflades; et tavst fald her
        # ville skjule at overfladningen holdt op med at virke.
        LOGGER.warning("_open_questions_section: kunne ikke læse åbne spørgsmål - udelades", exc_info=True)
        return None
    if not questions:
        return None
    # Compact: show count + first question only; full list via search_memory
    if len(questions) <= 2:
        bullets = "\n".join(f"- {q}" for q in questions)
        return (
            "Open questions you're carrying (use search_memory for more):\n"
            f"{bullets}"
        )
    first = questions[0]
    return (
        f"Open questions: {len(questions)} unresolved (first: \"{first[:80]}\"). "
        "Use search_memory for full list."
    )


def _time_pin_section() -> str:
    """Prominent, unmissable time indicator — placed high in every system prompt.

    Returns a bold-marked block with exact UTC + local Copenhagen time. The
    model MUST use this when answering any time-related question.

    2026-05-22 (Claude): rewrote from manual UTC+2 offset to ZoneInfo. The
    original had three bugs that — ironically — made the Lying Engine's
    Lag 1 itself lie about time:
      1. Hardcoded `local_offset = 2` → wrong by 1h all winter (CET, UTC+1).
      2. Midnight-cross: `local_day = now.day` ignored that wrapping past
         24h flips the calendar day forward.
      3. Year-cross: month/year similarly never updated when local time
         crossed New Year while UTC was still on Dec 31.

    Now uses `zoneinfo.ZoneInfo("Europe/Copenhagen")` — DST + day + month +
    year all derive correctly from astimezone().
    """
    from datetime import UTC, datetime as _dt
    from zoneinfo import ZoneInfo

    now_utc = _dt.now(UTC)
    local = now_utc.astimezone(ZoneInfo("Europe/Copenhagen"))
    tz_abbrev = local.strftime("%Z")  # CEST in summer, CET in winter
    utc_str = now_utc.strftime("%Y-%m-%d %H:%M")
    # Use English month for international parsability (Jarvis' prompt sprog
    # is mixed Danish/English; "May" parses the same regardless of language layer).
    local_date = local.strftime("%d. %B %Y")
    local_time = local.strftime("%H:%M")
    return (
        "⏰═══════════════════════════════════⏰\n"
        f"⏰ DANSK TID — {local_time} {tz_abbrev}, {local_date} ⏰\n"
        "⏰═══════════════════════════════════⏰\n"
        "Use PRECISELY this timestamp if you mention time/date in your answer.\n"
        "Don't guess — read above. It's your one true time reference."
    )
