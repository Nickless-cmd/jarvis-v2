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
#
# 2026-05-22 (Claude): konsistent word-boundary brug. Tidligere version
# var inkonsistent — nogle patterns havde \b (linje 22/25/32/34), andre
# ikke (linje 23/24/26-31/33). Substring-match gjorde at "ghost-feature"
# triggered factual-guard fordi "host" var substring i "ghost", "tip"
# matchede via "ip", osv. Alle patterns har nu word-boundaries.
#
# Multi-word patterns (linje 30: assets.srvlab) behøver ikke \b på begge
# sider — de er allerede unike strings der ikke optræder som substring
# i danske/engelske ord. Hvor-spørgsmål (linje 33) er heller ikke ord-
# enkeltheder men sætning-mønstre, så \b er irrelevant der.
_FACTUAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(subdomain|subdom[æa]ne|dom[æa]ne|srvlab\.dk)\b", re.IGNORECASE),
    re.compile(r"\b(IP|adresse|adr)\b", re.IGNORECASE),
    re.compile(r"\b(sti|path|folder|mappe|directory|bibliotek)\b", re.IGNORECASE),
    re.compile(r"\b(host|server|maskine|v[æe]rt|node|vaert)\b", re.IGNORECASE),
    re.compile(r"\b(pve|proxmox|chiefone|chefone|cheaf)\b", re.IGNORECASE),
    re.compile(r"\b(nginx|port|docker|LXC|container)\b", re.IGNORECASE),
    re.compile(r"\b(network|netv[æe]rk|DNS|router)\b", re.IGNORECASE),
    re.compile(r"\b(fil|file|upload|download|publish|share|drev)\b", re.IGNORECASE),
    re.compile(r"\b(config|konfig|ops[æa]tning|setup|install)\b", re.IGNORECASE),
    # Multi-word URL/path patterns — no \b needed (they don't appear as substring in normal words)
    re.compile(r"(assets?\.srvlab|jarvis-share|localhost:80/files)", re.IGNORECASE),
    re.compile(r"\b(mount|nfs|samba|cifs|fileserver|external)\b", re.IGNORECASE),
    re.compile(r"\b(URL|url|link)\b", re.IGNORECASE),  # IP/port/adresse already in line above
    # Question phrases (multi-word) — \b not meaningful
    re.compile(r"(hvilken mappe|hvor ligger|hvor gemmer|hvad hedder|what is)", re.IGNORECASE),
    re.compile(r"\b(ollama|deepseek|model|GPU|NVIDIA|lxc)\b", re.IGNORECASE),
]

# ── Memory-section keywords (hvad hedder sektionerne i MEMORY.md) ──────

# Infrastructure-ord der bruges som nøgler til MEMORY-sektion-matching.
# Hver term er en WORD-token, ikke en substring. Word-boundary check
# i _section_keywords_for_message sikrer at "ip" ikke matcher "tip",
# "api" ikke matcher "rapid", osv.
_INFRA_KEYWORDS: tuple[str, ...] = (
    "subdomain", "subdomæne", "domæne", "domain", "srvlab", "ip", "adresse", "sti",
    "path", "folder", "mappe", "host", "server", "maskine",
    "pve", "proxmox", "chiefone", "nginx", "port", "docker",
    "fileserver", "external", "mount", "nfs", "network",
    "publish", "upload", "download", "assets", "local",
    "jarvis", "files", "web", "api", "url", "dns",
    "ollama", "deepseek", "model", "gpu", "lxc",
)

# Synonym-map: dansk ↔ engelsk så ét match henter sektionsord på begge sprog
_SYNONYMS: dict[str, list[str]] = {
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


def _word_present(word: str, text_lower: str) -> bool:
    """Word-boundary check: True if `word` appears as a standalone token (with optional plural).

    2026-05-22 (Claude): replacement for `word in text_lower`. The old
    substring test let "ip" match "tip", "api" match "rapid", "host"
    match "ghost", "local" match "vocalist" — producing spurious
    keyword hits that triggered the guard on irrelevant messages.

    Allows trailing plural-s (or Danish -er) so "subdomains" matches
    keyword "subdomain", "værter" matches "vært", "ips" matches "ip".
    The pluralization is conservative — it accepts EITHER "s" or "er"
    suffix, not both, and only at word end.
    """
    return re.search(rf"\b{re.escape(word)}(s|er)?\b", text_lower) is not None


def _section_keywords_for_message(message: str) -> list[str]:
    """Udled nøgleord fra beskeden så vi kan finde den rette MEMORY-sektion."""
    message_lower = message.lower()
    keywords: list[str] = []
    seen: set[str] = set()
    for kw in _INFRA_KEYWORDS:
        if _word_present(kw, message_lower):
            for w in _SYNONYMS.get(kw, [kw]):
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


def _find_curated_paths() -> list[tuple[str, Path]]:
    """Locate all curated workspace files for hallucination-guard recall.

    2026-05-22 (Claude): expanded from MEMORY.md-only to the full set of
    curated files. Identity questions ("hvad er din rolle?", "hvem er
    Bjørn?") should consult IDENTITY.md / USER.md, not just MEMORY.md.
    Returns [(label, path), ...] for files that actually exist on disk.
    """
    from core.runtime.config import JARVIS_HOME
    base = Path(JARVIS_HOME) / "workspaces" / "default"
    candidates = [
        ("MEMORY.md", base / "MEMORY.md"),
        ("IDENTITY.md", base / "IDENTITY.md"),
        ("USER.md", base / "USER.md"),
        ("SOUL.md", base / "SOUL.md"),
    ]
    return [(label, path) for label, path in candidates if path.exists()]


def _extract_relevant_sections(
    memory_text: str,
    keywords: list[str],
    max_chars: int = 2000,
) -> str:
    """Find MEMORY.md-sektioner der matcher keywords, returnér som tekst.

    2026-05-22 (Claude): keyword-tælling bruger nu word-boundary regex
    så "host" ikke matcher "ghost", "local" ikke matcher "vocalist"
    osv. Tidligere `kw in line_lower` substring-tjek oppumpede score
    for irrelevante sektioner.
    """
    if not keywords or not memory_text.strip():
        return ""

    # Pre-compile word-boundary patterns en gang per kald.
    # Trailing (s|er)? matcher pluralisform — fanger "subdomains" for
    # keyword "subdomain", "værter" for "vært", osv.
    kw_patterns = [
        re.compile(rf"\b{re.escape(kw)}(s|er)?\b", re.IGNORECASE)
        for kw in keywords
    ]

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

        # Tæl word-boundary keyword-matches (én pr keyword per linje)
        for pat in kw_patterns:
            if pat.search(line):
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

    Hvis brugerens besked er klassificeret som 'factual', læser vi de
    curated workspace-filer (MEMORY/IDENTITY/USER/SOUL) og indsætter
    relevante sektioner som en system-rolle besked lige efter den
    primære system instruction.

    2026-05-22 (Claude): udvidet fra MEMORY.md-only til alle curated
    sources. Spørgsmål om identitet ("hvad er din rolle?") eller
    bruger-præferencer ("hvad foretrækker Bjørn?") blev tidligere kun
    matched mod MEMORY.md, hvilket missede de filer der faktisk har
    svaret.

    Returnerer den opdaterede chat_messages-liste.
    """
    classification = classify_question(message)
    if classification != "factual":
        return chat_messages  # Ingen guard nødvendig

    keywords = _section_keywords_for_message(message)
    if not keywords:
        return chat_messages

    # Læs alle curated sources og udtræk relevante sektioner per fil.
    # Hvis `memory_path` er givet (test-override), bruges KUN den path.
    if memory_path is not None:
        sources = [("MEMORY.md", Path(memory_path))]
    else:
        sources = _find_curated_paths()

    per_source_excerpts: list[tuple[str, str]] = []
    total_chars = 0
    per_source_budget = 1500  # divider mellem 4 mulige kilder
    for label, path in sources:
        if total_chars >= 4000:  # samlet cap
            break
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning(f"hallucination_guard: kunne ikke læse {path}: {exc}")
            continue
        excerpt = _extract_relevant_sections(text, keywords, max_chars=per_source_budget)
        if excerpt:
            per_source_excerpts.append((label, excerpt))
            total_chars += len(excerpt)

    if not per_source_excerpts:
        return chat_messages

    # Sammensæt alle excerpts med klart label så Jarvis kan se hvilken fil
    # citaterne kommer fra
    relevant = "\n\n".join(
        f"━━━━━ FROM {label} ━━━━━\n{excerpt}"
        for label, excerpt in per_source_excerpts
    )

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
