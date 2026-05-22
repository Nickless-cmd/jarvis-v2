"""Hallucination Guard — tvungen memory-check før svar.

Injectes i visible model prompt som en ekstra system-rolle besked når
brugerens spørgsmål matcher faktuelle infrastruktur-emner. Tvinger mig
til at se hvad jeg faktisk ved, i stedet for at gætte.
"""

from __future__ import annotations

import re
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Trigger-mønstre ────────────────────────────────────────────────────
# Når brugerens besked matcher disse, slår guard'en til.

_FACTUAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"(subdomain|subdom[æa]ne|dom[æa]ne|srvlab\.dk)", re.IGNORECASE),
    re.compile(r"\b(IP|adresse|adr)\b", re.IGNORECASE),
    re.compile(r"(sti|path|folder|mappe|directory|bibliotek)", re.IGNORECASE),
    re.compile(r"(host|server|maskine|v[æe]rt|node|vaert)", re.IGNORECASE),
    re.compile(r"\b(pve|proxmox|chiefone|chefone|cheaf)\b", re.IGNORECASE),
    re.compile(r"(nginx|port|docker|LXC|container)", re.IGNORECASE),
    re.compile(r"(network|netv[æe]rk|DNS|router)", re.IGNORECASE),
    re.compile(r"(fil|file|upload|download|publish|share|drev)", re.IGNORECASE),
    re.compile(r"(config|konfig|ops[æa]tning|setup|install)", re.IGNORECASE),
    re.compile(r"(assets?\.srvlab|jarvis-share|localhost:80/files)", re.IGNORECASE),
    re.compile(r"(mount|nfs|samba|cifs|fileserver|external)", re.IGNORECASE),
    re.compile(r"\b(IP|IP-adresse|adresse|port|URL|url|link)\b", re.IGNORECASE),
    re.compile(r"(hvilken mappe|hvor ligger|hvor gemmer|hvad hedder|what is)", re.IGNORECASE),
    re.compile(r"\b(ollama|deepseek|model|GPU|NVIDIA|lxc|container)\b", re.IGNORECASE),
]

# ── Memory-section keywords (hvad hedder sektionerne i MEMORY.md) ──────

def _section_keywords_for_message(message: str) -> list[str]:
    """Udled nøgleord fra beskeden, så vi kan finde den rette MEMORY-sektion."""
    message_lower = message.lower()
    keywords = []
    # Infrastructure-ord
    infra_keywords = [
        "subdomain", "subdomæne", "domæne", "domain", "srvlab", "ip", "adresse", "sti",
        "path", "folder", "mappe", "host", "server", "maskine",
        "pve", "proxmox", "chiefone", "nginx", "port", "docker",
        "fileserver", "external", "mount", "nfs", "network",
        "publish", "upload", "download", "assets", "local",
        "jarvis", "files", "web", "api", "url", "dns",
        "ollama", "deepseek", "model", "gpu", "lxc",
    ]
    # Synonym-map: dansk → engelsk og omvendt, så vi matcher MEMORY.md på tværs af sprog
    _synonyms: dict[str, list[str]] = {
        "subdomæne": ["subdomain", "subdomæne"],
        "domæne": ["domain", "domæne"],
        "mappe": ["folder", "mappe"],
        "sti": ["path", "sti"],
        "maskine": ["machine", "node", "maskine"],
        "vært": ["host", "vært"],
        "netværk": ["network", "netværk"],
        "drev": ["drive", "drev"],
        "subdomain": ["subdomain", "subdomæne"],
        "folder": ["folder", "mappe"],
        "path": ["path", "sti"],
        "machine": ["machine", "maskine", "node"],
        "host": ["host", "vært"],
        "network": ["network", "netværk"],
        "drive": ["drive", "drev"],
    }
    seen: set[str] = set()
    for kw in infra_keywords:
        if kw in message_lower:
            # Tilføj hovedordet og alle synonymer
            to_add = _synonyms.get(kw, [kw])
            for w in to_add:
                if w not in seen:
                    keywords.append(w)
                    seen.add(w)
    return keywords


def classify_question(message: str) -> str:
    """Klassificér beskeden: 'factual' | 'casual' | 'tool_call'.

    'factual' = spørgsmål om infrastruktur, IP, stier, subdomains mv.
    'tool_call' = brugeren beder om en handling, ikke et fakta-svar.
    'casual' = alt andet (smalltalk, refleksion, følelser).
    """
    message = message.strip()

    # Tool calls og korte opfordringer
    if any(
        message.startswith(prefix)
        for prefix in ("kør", "byg", "skriv", "opret", "slet", "hent", "gør", "vis")
    ):
        return "tool_call"

    # Korte beskeder (< 5 ord) uden faktaord
    word_count = len(message.split())
    if word_count < 5:
        has_factual = any(p.search(message) for p in _FACTUAL_PATTERNS)
        if not has_factual:
            return "casual"

    # Tjek mod fakta-mønstre
    if any(p.search(message) for p in _FACTUAL_PATTERNS):
        return "factual"

    return "casual"


def _find_memory_path() -> Path:
    """Find MEMORY.md — kig i runtime workspace først, derefter repo."""
    from core.runtime.config import JARVIS_HOME
    candidates = [
        Path(JARVIS_HOME) / "workspaces" / "default" / "MEMORY.md",
        Path(JARVIS_HOME) / "MEMORY.md",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _extract_relevant_sections(
    memory_text: str,
    keywords: list[str],
    max_chars: int = 2000,
) -> str:
    """Find MEMORY.md-sektioner der matcher keywords, returnér som tekst."""
    if not keywords or not memory_text.strip():
        return ""

    lines = memory_text.split("\n")
    sections: list[dict[str, Any]] = []  # each: {"heading": str, "content": str, "score": int}
    current_heading = "(top)"
    current_content: list[str] = []
    current_score = 0

    for line in lines:
        # Er dette en heading?
        heading_match = re.match(r"^(#{1,4})\s+(.+)$", line)
        if heading_match:
            # Gem forrige sektion
            if current_content and current_score > 0:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content),
                    "score": current_score,
                })
            level = len(heading_match.group(1))
            current_heading = ("  " * (level - 1)) + heading_match.group(2)
            current_content = [line]
            current_score = 0
        else:
            current_content.append(line)

        # Tæl keyword-matches
        line_lower = line.lower()
        for kw in keywords:
            if kw in line_lower:
                current_score += 1

    # Gem sidste sektion
    if current_content and current_score > 0:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_content),
            "score": current_score,
        })

    if not sections:
        return ""

    # Sortér efter score, tag top 3
    sections.sort(key=lambda s: s["score"], reverse=True)
    top = sections[:3]

    result_parts: list[str] = []
    char_count = 0
    for sec in top:
        text = f"### {sec['heading']}\n{sec['content']}\n"
        if char_count + len(text) > max_chars:
            # Truncér sidste sektion
            allowed = max_chars - char_count
            if allowed > 80:
                text = text[:allowed] + "\n[...truncated]"
                result_parts.append(text)
            break
        result_parts.append(text)
        char_count += len(text)

    return "\n".join(result_parts)


def inject_memory_into_prompt(
    message: str,
    chat_messages: list[dict[str, str]],
    *,
    memory_path: str | None = None,
) -> list[dict[str, str]]:
    """Injectér relevant memory som en system-rolle besked i prompten.

    Hvis brugerens besked er klassificeret som 'factual', læser vi
    MEMORY.md og indsætter relevante sektioner som en system-rolle
    besked lige efter den primære system instruction.

    Returnerer den opdaterede chat_messages-liste.
    """
    classification = classify_question(message)
    if classification != "factual":
        return chat_messages  # Ingen guard nødvendig

    keywords = _section_keywords_for_message(message)
    if not keywords:
        return chat_messages

    # Læs MEMORY.md
    mem_path = Path(memory_path) if memory_path else _find_memory_path()
    try:
        memory_text = mem_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning(f"hallucination_guard: kunne ikke læse {mem_path}: {exc}")
        return chat_messages

    relevant = _extract_relevant_sections(memory_text, keywords)
    if not relevant:
        return chat_messages

    # Byg guard-besked — sæt den som en system-rolle besked
    # Vi indsætter den EFTER den primære system instruction (første system-message)
    # så den stadig er synlig men ikke overskriver den primære instruktion.
    #
    # 2026-05-22 (Claude): styrket forfatningssproget efter Codex+Bjørn
    # diagnose. Tidligere version sagde "Svar KUN baseret på dette" men
    # blev rutinemæssigt ignoreret. Ny version:
    #  - er eksplicit om "fabuler ikke"
    #  - giver en konkret fallback-sætning at sige hvis info mangler
    #  - peger på read_self_docs som verificerbar tool-vej
    #  - signalerer at provenance er regel ([MEMORY.md] vs [DAILY])
    guard_message = {
        "role": "system",
        "content": (
            "[HALLUCINATION GUARD — HÅRDT HUKOMMELSES-KRAV]\n"
            "\n"
            "Brugeren stiller et fakta-spørgsmål om dit eget system / "
            "infrastruktur. Følg denne procedure ord-for-ord:\n"
            "\n"
            "1. LÆS de relevante MEMORY.md-sektioner herunder.\n"
            "2. Hvis svaret står i sektionerne → citér det. Brug "
            "provenance-prefix [MEMORY.md] kun hvis claim faktisk findes "
            "i MEMORY.md-uddraget herunder.\n"
            "3. Hvis svaret IKKE står herunder → svar præcist: "
            "\"Det står ikke i min hukommelse — jeg vil hellere tjekke "
            "med et tool end gætte.\" og kald derefter read_self_docs / "
            "search_memory / read_file.\n"
            "4. FABULÉR IKKE infrastruktur-detaljer (URL'er, paths, "
            "subdomains, IP-adresser, mappe-strukturer). Disse ER fakta, "
            "ikke gæt-bare-emner. En gæt der lyder rimeligt forstyrrer "
            "Bjørn mere end et ærligt \"ved ikke\".\n"
            "5. Hvis du tidligere har sagt noget om dette emne i samtalen, "
            "antag det kan have været forkert — gå til MEMORY.md igen, "
            "ikke tilbage til din egen tidligere besked.\n"
            "\n"
            "── MEMORY.md-uddrag (kanonisk kilde) ──\n"
            f"{relevant}\n"
            "── slut MEMORY.md ──\n"
        ),
    }

    # Find den sidste system-besked og indsæt efter den
    # (så den primære system instruction bevares som den første)
    last_system_idx = -1
    for i, msg in enumerate(chat_messages):
        if msg.get("role") == "system":
            last_system_idx = i

    if last_system_idx >= 0:
        chat_messages.insert(last_system_idx + 1, guard_message)
    else:
        # Ingen system-besked — indsæt før user message
        chat_messages.insert(0, guard_message)

    # Log: tæller sektioner via heading-markører, ikke characters.
    # 2026-05-22 (Claude): tidligere log brugte len(relevant) (char count)
    # som "sections=" — misvisende.
    section_count = relevant.count("###")
    logger.info(
        "hallucination_guard injected for factual question "
        f"(keywords={keywords}, sections={section_count}, chars={len(relevant)})"
    )
    return chat_messages
