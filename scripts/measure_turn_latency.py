#!/usr/bin/env python3
"""Mål Jarvis' svartid — fra send til svar.

To tilstande:

  --watch      PASSIV. Overvåger en aktiv session og rapporterer, for hver ny
               tur, tiden fra brugerens besked er gemt til assistentens svar er
               gemt — plus hvilken provider der betjente turen. Rører intet.

  --probe      AKTIV. Opretter en session som owner og sender identiske beskeder
               skiftevis via deepseek og ollama-cloud, og måler TO ting:
                 TTFB   tid til første synlige tegn  (det brugeren oplever)
                 total  tid til svaret er færdigt

Den aktive tilstand er den rene måling: samme prompt, samme session, kun
provideren varierer. Den passive måler virkeligheden, inklusive alt det der
sker rundt om — tool-runder, godkendelser, køtid.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "http://127.0.0.1:8080"
DB = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"
OUT = Path.home() / ".jarvis-v2" / "files" / "latency" / "turns.jsonl"


def _token() -> str:
    cfg = Path.home() / ".jarvis-v2" / "config" / "runtime.json"
    return str(json.loads(cfg.read_text(encoding="utf-8")).get("system_api_token") or "")


def _parse(ts: str):
    try:
        d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ── PASSIV ──────────────────────────────────────────────────────────────────

def _turns(session_id: str, limit: int = 40) -> list[dict]:
    """Par bruger-besked med det følgende assistent-svar."""
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT id, role, created_at, substr(content,1,90) FROM chat_messages "
        "WHERE session_id=? AND role IN ('user','assistant') "
        "ORDER BY id DESC LIMIT ?", (session_id, limit)).fetchall()
    rows.reverse()
    out = []
    for i, r in enumerate(rows):
        if r[1] != "user":
            continue
        nxt = next((x for x in rows[i + 1:] if x[1] == "assistant"), None)
        if not nxt:
            continue
        a, b = _parse(r[2]), _parse(nxt[2])
        if not a or not b:
            continue
        out.append({"user_id": r[0], "asked_at": r[2], "answered_at": nxt[2],
                    "seconds": round((b - a).total_seconds(), 1),
                    "prompt": (r[3] or "").replace("\n", " ")[:70]})
    return out


def _provider_for(asked_at: str, answered_at: str) -> str:
    """Hvilken provider betjente turen.

    visible_runs har baade tidsrammen OG provideren. Cost-raekken skrives
    FOERST efter at svaret er gemt (maalt: assistent 20:56:14, cost 20:57:27),
    saa et vindue der slutter ved svaret rammer aldrig noget — den fejl kostede
    mig foerste maaling.
    """
    c = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    row = c.execute(
        "SELECT run_id, provider FROM visible_runs "
        "WHERE started_at >= ? AND started_at <= ? "
        "ORDER BY started_at DESC LIMIT 1",
        (asked_at, answered_at)).fetchone()
    if not row:
        return "?"
    run_id, prov = row[0], row[1] or "?"
    m = c.execute(
        "SELECT model, SUM(input_tokens), SUM(output_tokens) FROM costs "
        "WHERE run_id = ? GROUP BY model ORDER BY 3 DESC LIMIT 1", (run_id,)).fetchone()
    if not m:
        return str(prov)
    return f"{prov}/{m[0]} in={m[1]} out={m[2]}"


def watch(session_id: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    seen = {t["user_id"] for t in _turns(session_id)}
    print(f"  overvåger {session_id}")
    print(f"  {len(seen)} eksisterende ture ignoreres — kun NYE måles")
    print("  (Ctrl-C for at stoppe)\n")
    print("  %-8s %-9s  %s" % ("sekunder", "provider", "besked"))
    while True:
        for t in _turns(session_id):
            if t["user_id"] in seen:
                continue
            seen.add(t["user_id"])
            t["provider"] = _provider_for(t["asked_at"], t["answered_at"])
            with OUT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(t, ensure_ascii=False) + "\n")
            print("  %8.1f %-9s  %s" % (
                t["seconds"], t["provider"].split("/")[0][:9], t["prompt"]))
        time.sleep(3)


# ── AKTIV ───────────────────────────────────────────────────────────────────

def _api(path: str, payload: dict | None = None, stream: bool = False):
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + _token(),
                 "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    return urllib.request.urlopen(req, timeout=600)


def probe(rounds: int, message: str) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with _api("/chat/sessions", {"title": "latency-probe (Opus)"}) as r:
        sess = json.loads(r.read())
    # Svaret er indpakket: {"session": {"id": ...}}
    inner = sess.get("session") if isinstance(sess.get("session"), dict) else sess
    sid = str(inner.get("id") or inner.get("session_id") or "")
    print(f"  session oprettet: {sid}\n")
    print("  %-9s %-6s %8s %8s %7s  %s" % (
        "provider", "runde", "TTFB", "total", "tegn", "start på svar"))

    for rnd in range(1, rounds + 1):
        for prov, model in (("deepseek", "deepseek-v4-flash"),
                            ("ollama", "deepseek-v4-flash:cloud")):
            payload = {"session_id": sid, "message": message,
                       "provider_choice": prov, "model": model,
                       "approval_mode": "trust", "thinking_mode": "think"}
            t0 = time.time()
            ttfb = None
            chars = 0
            head = ""
            try:
                with _api("/chat/stream/v2", payload) as resp:
                    for raw in resp:
                        line = raw.decode("utf-8", "replace").strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            ev = json.loads(line[5:].strip())
                        except Exception:
                            continue
                        if ev.get("type") == "content_block_delta":
                            piece = ((ev.get("delta") or {}).get("text") or "")
                            if piece and ttfb is None:
                                ttfb = time.time() - t0
                            chars += len(piece)
                            if len(head) < 60:
                                head += piece
                        if ev.get("type") == "message_stop":
                            break
                total = time.time() - t0
            except Exception as exc:
                print("  %-9s %-6d  FEJL: %s" % (prov, rnd, str(exc)[:60]))
                continue
            rec = {"ts": datetime.now(timezone.utc).isoformat(), "mode": "probe",
                   "session_id": sid, "round": rnd, "provider": prov, "model": model,
                   "ttfb_s": round(ttfb or 0, 2), "total_s": round(total, 2),
                   "chars": chars}
            with OUT.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            print("  %-9s %-6d %7.2fs %7.2fs %7d  %s" % (
                prov, rnd, ttfb or 0, total, chars, head.replace("\n", " ")[:56]))
            time.sleep(3)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--watch", default="", help="session-id at overvåge passivt")
    ap.add_argument("--probe", action="store_true", help="aktiv A/B som owner")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--message", default="Giv mig en kort status på dig selv lige nu.")
    a = ap.parse_args()
    if a.watch:
        watch(a.watch)
    elif a.probe:
        probe(a.rounds, a.message)
    else:
        ap.print_help()
