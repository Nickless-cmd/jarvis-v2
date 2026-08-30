"""Prompt-cache-sonde — find hvad der bryder prefix-cachen MELLEM to rigtige ture.

Baggrund (2026-08-29): DeepSeeks ``prompt_cache_hit_tokens`` stod frosset på
præcis 6400 mens input voksede 78k→103k. Et syntetisk forsøg — samme assembly
bygget to gange i træk — viste beskeds-arrayet byte-stabilt gennem 49 beskeder
og 113.529 tegn. Altså kan bruddet ikke reproduceres på sekunder.

Det er selve pointen: de sektioner der mistænkes (``cognitive_state`` ~7k tegn,
mood, puls, hardware) opdateres på MINUT-skala. To kald i træk ser ens ud; to
rigtige ture gør ikke. Sonden skal derfor sidde i den ægte sti og sammenligne
to på-hinanden-følgende ture.

DeepSeeks regel (api-docs, "Context Caching"): et svar rammer kun cachen hvis
det *fully matches* en cache-prefix-enhed, og enheder skæres ved besked-grænser
og faste token-intervaller. Derfor er det eneste tal der betyder noget:
**hvor langt rækker det byte-identiske prefix før første afvigelse.**

Slukket som standard. Tænd med::

    touch /tmp/jarvis-msgdump

Så skriver hver synlig tur ``/tmp/jarvis-msgdumps/latest.json`` (forrige
roteres til ``prev.json``) og printer én linje til stderr::

    PROMPT-CACHE-PROBE stable_prefix_chars=113529 msgs_stable=49/50 \
        first_diff=#49 role=user offset=1526

Sammenlignings-logikken er ren og side-effekt-fri → unit-testbar uden disk.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

GATE_PATH = "/tmp/jarvis-msgdump"
DUMP_DIR = "/tmp/jarvis-msgdumps"

# Hvor meget kontekst omkring bruddet der vises i stderr-linjen. Kort med vilje:
# linjen skal kunne læses i journalen uden at drukne den.
_EXCERPT = 90


@dataclass(slots=True)
class ProbeVerdict:
    """Resultatet af at sammenligne to beskeds-arrays."""

    stable_prefix_chars: int = 0
    msgs_stable: int = 0
    msgs_total: int = 0
    first_diff_index: int | None = None
    first_diff_role: str = ""
    first_diff_offset: int = 0
    excerpt_a: str = ""
    excerpt_b: str = ""
    identical: bool = False
    sections: list[str] = field(default_factory=list)

    def as_line(self) -> str:
        if self.identical:
            return (f"PROMPT-CACHE-PROBE identiske msgs={self.msgs_total} "
                    f"stable_prefix_chars={self.stable_prefix_chars}")
        return (
            f"PROMPT-CACHE-PROBE stable_prefix_chars={self.stable_prefix_chars} "
            f"msgs_stable={self.msgs_stable}/{self.msgs_total} "
            f"first_diff=#{self.first_diff_index} role={self.first_diff_role} "
            f"offset={self.first_diff_offset}"
        )


def flatten(items: list[dict]) -> list[tuple[str, str]]:
    """Fold provider-item-formen ud til (rolle, tekst).

    Håndterer både ``content`` som streng og som liste af blokke — de synlige
    adaptere bruger begge former.
    """
    out: list[tuple[str, str]] = []
    for it in items or []:
        try:
            role = str(it.get("role") or "")
            content = it.get("content")
            if isinstance(content, str):
                text = content
            else:
                text = "".join(
                    str(c.get("text", "")) for c in (content or [])
                    if isinstance(c, dict)
                )
            out.append((role, text))
        except Exception:
            out.append(("?", ""))
    return out


def compare(prev: list[tuple[str, str]], cur: list[tuple[str, str]]) -> ProbeVerdict:
    """Find hvor langt det byte-identiske prefix rækker. Ren funktion.

    ``stable_prefix_chars`` er summen af tegn i de beskeder der er ens fra
    starten — altså præcis det DeepSeek kan genbruge. Første afvigende besked
    rapporteres med tegn-offset, så synderen kan udpeges uden gætteri.
    """
    v = ProbeVerdict(msgs_total=max(len(prev), len(cur)))
    for i in range(max(len(prev), len(cur))):
        a = prev[i] if i < len(prev) else None
        b = cur[i] if i < len(cur) else None
        if a is not None and b is not None and a == b:
            v.stable_prefix_chars += len(a[1])
            v.msgs_stable += 1
            continue
        # Første afvigelse — beskriv den og stop.
        v.first_diff_index = i
        ta = a[1] if a else ""
        tb = b[1] if b else ""
        v.first_diff_role = (a[0] if a else (b[0] if b else "-"))
        off = next(
            (k for k in range(min(len(ta), len(tb))) if ta[k] != tb[k]),
            min(len(ta), len(tb)),
        )
        v.first_diff_offset = off
        v.excerpt_a = ta[max(0, off - _EXCERPT // 2): off + _EXCERPT]
        v.excerpt_b = tb[max(0, off - _EXCERPT // 2): off + _EXCERPT]
        v.sections = _nearby_sections(ta, off)
        return v
    v.identical = True
    return v


def _nearby_sections(text: str, offset: int) -> list[str]:
    """De sidste sektions-overskrifter før bruddet — peger på synderen.

    Prompten mærker sektioner med ``[NAVN]``-linjer og ``·``-punkter; vi tager
    de nærmeste to før offset så rapporten siger *hvilken* del der muterede.
    """
    try:
        head = text[:offset]
        heads = [
            ln.strip() for ln in head.splitlines()
            if ln.strip().startswith("[") or ln.strip().startswith("###")
        ]
        return heads[-2:]
    except Exception:
        return []


def enabled() -> bool:
    """Sonden er slukket med mindre gate-filen findes."""
    try:
        return os.path.exists(GATE_PATH)
    except Exception:
        return False


def probe(items: list[dict], *, session_id: str = "") -> ProbeVerdict | None:
    """Skriv turens beskeds-array og sammenlign med forrige tur.

    Self-safe: må ALDRIG kaste ind i den synlige svar-sti. Returnerer dommen
    når der var en forrige tur at sammenligne med, ellers ``None``.
    """
    if not enabled():
        return None
    try:
        os.makedirs(DUMP_DIR, exist_ok=True)
        cur = flatten(items)
        payload = {
            "session_id": session_id,
            "messages": [
                {
                    "role": r,
                    "chars": len(t),
                    "sha256": hashlib.sha256(t.encode("utf-8", "replace")).hexdigest()[:16],
                    "text": t,
                }
                for r, t in cur
            ],
        }
        latest = os.path.join(DUMP_DIR, "latest.json")
        prev_path = os.path.join(DUMP_DIR, "prev.json")

        verdict: ProbeVerdict | None = None
        if os.path.exists(latest):
            try:
                with open(latest, "r", encoding="utf-8") as fh:
                    old = json.load(fh)
                # Sammenlign kun inden for samme session — ellers er forskellen
                # triviel og siger intet om cachen.
                if str(old.get("session_id") or "") == str(session_id or ""):
                    prev_msgs = [
                        (str(m.get("role") or ""), str(m.get("text") or ""))
                        for m in (old.get("messages") or [])
                    ]
                    verdict = compare(prev_msgs, cur)
                os.replace(latest, prev_path)
            except Exception:
                pass

        tmp = latest + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False)
        os.replace(tmp, latest)

        if verdict is not None:
            import sys
            print(verdict.as_line(), file=sys.stderr, flush=True)
            if not verdict.identical:
                print(f"  A: {verdict.excerpt_a!r}", file=sys.stderr, flush=True)
                print(f"  B: {verdict.excerpt_b!r}", file=sys.stderr, flush=True)
                if verdict.sections:
                    print(f"  sektion: {' | '.join(verdict.sections)}",
                          file=sys.stderr, flush=True)
        return verdict
    except Exception:
        return None
