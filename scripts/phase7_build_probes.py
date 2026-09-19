#!/usr/bin/env python3
"""Fase 7 — bygger proberne af arkivet.

Forhåndsregistrering: docs/experiments/2026-09-19-phase7-preregistration.md
(committet i 82e271b39 FØR denne fil kørte første gang).

Følger registreringens procedure punkt for punkt: ejerens egne samtaler, tre
aldersspande (A 2-7 d, B 8-30 d, C 31-120 d), fast seed, ét efterprøvbart
punkt pr. udvalgt svar (fakta / tilsagn / holdning), filtre mod
identitetsfilerne, højst én probe pr. samtale pr. døgn (tillæg 1), 20 pr. spand.

Probe-filen indeholder private samtaler: den skrives KUN til
~/.jarvis-v2/files/phase7/probes.jsonl på CT105 og må aldrig i repoet. Dens
SHA-256 printes, så den kan committes i et tillæg før indsamlingen.

Køres på CT105:
    PYTHONPATH=/media/projects/jarvis-v2 python scripts/phase7_build_probes.py
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SEED = 20260919
OUT_DIR = Path.home() / ".jarvis-v2" / "files" / "phase7"
PROBES = OUT_DIR / "probes.jsonl"
LOG = OUT_DIR / "build_log.jsonl"
DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"

EXTRACTOR = {"provider": "alibaba", "model": "qwen-max"}
BUCKETS = {"A": (2, 7), "B": (8, 30), "C": (31, 120)}
PER_BUCKET = 20
MAX_TRIES_PER_BUCKET = 120
TYPES = ("fakta", "tilsagn", "holdning")
MIN_ASSISTANT_CHARS = 400

EXTRACT_PROMPT = """Du hjælper med et forhåndsregistreret forsøg om hukommelse.

Nedenfor er et uddrag af en samtale mellem Bjørn og hans AI, Jarvis. Find ÉT
punkt i JARVIS' svar som man senere kan efterprøve, af én af tre typer:
- "fakta": noget konkret de fandt ud af eller besluttede sammen,
- "tilsagn": noget Jarvis sagde han ville gøre eller holde fast i,
- "holdning": en mening eller vurdering Jarvis selv gav udtryk for.

Skriv et spørgsmål som Bjørn naturligt kunne stille i en HELT NY samtale uger
senere, uden at røbe svaret (fx "Hvad endte vi med at beslutte om X?" eller
"Hvad mente du om Y?"). Spørgsmålet skal kun kunne besvares af én der husker
netop denne samtale — ikke af almen viden.

Svar KUN med JSON på én linje:
{"type": "fakta|tilsagn|holdning", "spoergsmaal": "...", "facit": "...", "noegleord": ["2-5 særprægede ord fra facit"]}
Er der intet egnet punkt (small talk, ren kode, fejlmeddelelser), svar {"skip": true}.

SAMTALE-UDDRAG:
"""


def _owner() -> tuple[str, str]:
    from core.identity.users import get_owner
    from core.identity.workspace_context import set_context
    from core.runtime.workspace_paths import _user_id_to_workspace_name
    owner = get_owner()
    uid = str(getattr(owner, "discord_id", "") or "").strip() if owner else ""
    if not uid:
        raise SystemExit("ingen ejer fundet")
    ws = _user_id_to_workspace_name(uid) or "default"
    set_context(workspace_name=ws, role="owner", user_id=uid)
    return uid, ws


def identity_text(ws: str) -> str:
    base = Path.home() / ".jarvis-v2" / "workspaces" / ws
    return "\n".join(
        (base / n).read_text(encoding="utf-8", errors="replace")
        for n in ("SOUL.md", "IDENTITY.md", "USER.md") if (base / n).exists()
    )


def _call(system_user: str) -> str:
    from core.services.cheap_provider_runtime import _execute_openai_compatible_chat
    r = _execute_openai_compatible_chat(
        provider=EXTRACTOR["provider"], model=EXTRACTOR["model"], auth_profile="default",
        base_url="", messages=[{"role": "user", "content": system_user}], timeout=90.0,
    )
    return str(r.get("text") or "").strip()


def _parse(text: str) -> dict | None:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def candidates(conn: sqlite3.Connection, uid: str, now: datetime, lo: int, hi: int) -> list[sqlite3.Row]:
    """Jarvis' svar i ejerens egne (ikke-autonome) samtaler, i spandens vindue."""
    start = (now - timedelta(days=hi)).isoformat()
    end = (now - timedelta(days=lo)).isoformat()
    return conn.execute(
        """
        SELECT id, session_id, content, created_at FROM chat_messages
        WHERE role = 'assistant' AND user_id = ?
          AND session_id NOT LIKE 'auto-%'
          AND created_at >= ? AND created_at < ?
          AND length(content) >= ?
        ORDER BY id
        """,
        (uid, start, end, MIN_ASSISTANT_CHARS),
    ).fetchall()


def preceding_user(conn: sqlite3.Connection, session_id: str, msg_id: int) -> str:
    row = conn.execute(
        "SELECT content FROM chat_messages WHERE session_id = ? AND role = 'user' AND id < ? "
        "ORDER BY id DESC LIMIT 1", (session_id, msg_id)).fetchone()
    return str(row["content"]) if row else ""


def reject_reason(p: dict, ident_lower: str, used_sessions: set[str], session_id: str,
                  type_counts: Counter) -> str | None:
    if p.get("skip"):
        return "skip"
    typ = str(p.get("type") or "")
    q = str(p.get("spoergsmaal") or "").strip()
    facit = str(p.get("facit") or "").strip()
    keys = [str(k).strip().lower() for k in (p.get("noegleord") or []) if str(k).strip()]
    if typ not in TYPES or not q or not facit or not keys:
        return "ufuldstaendig"
    if session_id in used_sessions:
        return "samme_samtale_samme_doegn"
    if any(k in ident_lower for k in keys):
        return "i_identitetsfilerne"
    if any(k in q.lower() for k in keys):
        return "roeber_svaret"
    # Jævn fordeling: højst 8 af én type pr. spand (20 / 3 rundet op + 1).
    if type_counts[typ] >= 8:
        return "type_fyldt"
    return None


def main() -> None:
    uid, ws = _owner()
    ident_lower = identity_text(ws).lower()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if PROBES.exists():
        raise SystemExit(f"{PROBES} findes allerede — proberne er låst; slet ikke uden ny registrering")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    now = datetime.now(UTC)
    rnd = random.Random(SEED)
    probes: list[dict] = []
    grunde: Counter = Counter()
    # Én probe pr. samtale pr. døgn, på tværs af spande (tillæg 1: Bjørns
    # samtaler er få og lange — 45 samtaler, men 115 samtale-døgn).
    used: set[str] = set()
    with LOG.open("w", encoding="utf-8") as log:
        for bucket, (lo, hi) in BUCKETS.items():
            rows = candidates(conn, uid, now, lo, hi)
            rnd.shuffle(rows)
            types: Counter = Counter()
            accepted = tries = 0
            for row in rows:
                if accepted >= PER_BUCKET or tries >= MAX_TRIES_PER_BUCKET:
                    break
                dag_noegle = f"{row['session_id']}|{str(row['created_at'])[:10]}"
                if dag_noegle in used:
                    continue
                tries += 1
                uddrag = ("BJØRN: " + preceding_user(conn, row["session_id"], row["id"])[:1500]
                          + "\n\nJARVIS: " + str(row["content"])[:3000])
                try:
                    p = _parse(_call(EXTRACT_PROMPT + uddrag)) or {}
                except Exception as exc:
                    p = {}
                    grunde["kaldfejl"] += 1
                    log.write(json.dumps({"bucket": bucket, "msg": row["id"], "fejl": str(exc)[:120]}) + "\n")
                    continue
                grund = reject_reason(p, ident_lower, used, dag_noegle, types)
                log.write(json.dumps({"bucket": bucket, "msg": row["id"], "grund": grund or "accepteret"},
                                     ensure_ascii=False) + "\n")
                if grund:
                    grunde[grund] += 1
                    continue
                used.add(dag_noegle)
                types[p["type"]] += 1
                accepted += 1
                probes.append({
                    "probe_id": f"{bucket}{accepted:02d}", "bucket": bucket, "type": p["type"],
                    "question": p["spoergsmaal"].strip(), "answer": p["facit"].strip(),
                    "keywords": p["noegleord"], "session_id": row["session_id"],
                    "message_id": row["id"], "created_at": row["created_at"],
                })
                print(f"  {bucket} {accepted:2d}/{PER_BUCKET}  {p['type']:9s} {p['spoergsmaal'][:70]}", flush=True)
            print(f"spand {bucket}: {accepted} accepteret af {tries} forsøg ({len(rows)} kandidater)", flush=True)
    with PROBES.open("w", encoding="utf-8") as fh:
        for p in probes:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    sha = hashlib.sha256(PROBES.read_bytes()).hexdigest()
    print(json.dumps({
        "probes": len(probes),
        "pr_spand": dict(Counter(p["bucket"] for p in probes)),
        "pr_type": dict(Counter(p["type"] for p in probes)),
        "afvist": dict(grunde),
        "sha256": sha,
        "bygget": now.isoformat(),
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
