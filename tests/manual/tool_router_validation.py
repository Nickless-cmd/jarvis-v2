"""Manual validation set for tool_router. Run before deploy.

Exercises 20 representative user messages across categories. Prints
selected_count + fallback flag + first 5 selected tools per case so a
human can sanity-check.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.services.tool_router import select_tools

CASES = [
    ("hej", "greeting"),
    ("god morgen", "greeting"),
    ("ja", "affirmation"),
    ("hmm", "ambiguous"),
    ("hvad sagde vi i går?", "memory"),
    ("husk at jeg hader broccoli", "memory"),
    ("hvad ved du om mig?", "memory-identity"),
    ("læs visible_runs.py", "code"),
    ("find alle steder hvor we use prompt_contract", "code-search"),
    ("commit ændringerne", "git"),
    ("vis mig din tilstand og lav et billede af din mood", "multi"),
    ("send en discord-besked til mig om vejret", "social-web"),
    ("hvor mange tokens bruger vi nu?", "system-introspection"),
    ("genstart heartbeat", "system-control"),
    ("hvem er du?", "identity"),
    ("hvad er din SOUL?", "identity"),
    ("", "empty"),
    ("?????", "junk"),
    ("kan du give mig en oversigt over alle decisions vi har truffet de sidste 7 dage og analysere om der er mønstre?", "long-substantive"),
    ("byg et nyt MC-widget der viser cpu", "project"),
]


def main() -> int:
    print(f"{'category':>20}  {'flag':>5}  {'count':>5}  {'conf':>5}  preview")
    print("-" * 110)
    for msg, cat in CASES:
        sel = select_tools(user_message=msg, session_id=None, lane="visible")
        print(
            f"{cat:>20}  {('FB' if sel.fallback_used else 'OK'):>5}  "
            f"{len(sel.selected_names):>5d}  {sel.confidence:>5.2f}  {msg!r}"
        )
        if not sel.fallback_used:
            print(f"{'':>20}  → first: {', '.join(sel.selected_names[:6])}")
            if sel.embedding_picks:
                print(f"{'':>20}  → emb-picks: {', '.join(sel.embedding_picks[:5])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
