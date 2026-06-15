"""Diagnosis-gate (spec 2026-06-14) — fanger uverificerede diagnostiske konklusioner.

Jarvis' eget konfabulations-mønster: han præsenterer en konklusion om system-tilstand
eller årsagssammenhæng ("broen er zombie", "containeren er 78 commits bagud", "wakeup'en
fyrede ikke") med høj selvtillid og specifikke detaljer — UDEN at have verificeret den.

Denne gate kører efter fact-gate, før output sendes. Den detekterer diagnostisk sprog og
tjekker om påstanden er verificeret i samme run (et ground-truth-tool blev kørt, ELLER
teksten refererer eksplicit til en verificering, ELLER teksten signalerer usikkerhed).

FASE 1 = ADVISORY (spec §2.3/§4): logger uverificerede diagnoser men BLOKERER IKKE.
Promotion til blocking sker efter data (≥14 dage) når heed-rate kendes.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Diagnostisk sprog: konklusioner om tilstand/årsag (ikke meninger eller fakta-med-kilde).
_DIAGNOSIS_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(er|var)\s+(orphaned|zombie|død|dead|stuck|hængt|blokeret|forældreløs|ikke\s+integreret|ikke\s+wiret|ikke\s+koblet)", re.I),
    re.compile(r"\b(fyrede\s+ikke|kom\s+ikke\s+(frem|igennem)|landede\s+aldrig|nåede\s+aldrig|blev\s+aldrig\s+(kaldt|kørt|trigget))", re.I),
    re.compile(r"\b\d+\s*commits?\s+(bagud|behind|foran|ahead)", re.I),
    re.compile(r"\b(findes\s+ikke|eksisterer\s+ikke|er\s+tom|er\s+væk|mangler\s+helt)\b", re.I),
    re.compile(r"\b(er\s+)?(deaktiveret|slået\s+fra|ikke\s+aktiv|aldrig\s+kørt|kører\s+ikke)\b", re.I),
]

# Usikkerheds-signaler → ikke en selvsikker diagnose (spec §2.4).
_UNCERTAINTY = re.compile(
    r"\b(jeg\s+tror|muligvis|måske|det\s+kan\s+(se\s+ud|være)|det\s+virker\s+som|"
    r"ser\s+ud\s+til|umiddelbart|formentlig|sandsynligvis|jeg\s+er\s+ikke\s+sikker|"
    r"hvis\s+jeg\s+husker|gætter|antager)\b", re.I)

# Verifikations-reference i teksten → påstanden ER underbygget (spec §2.2 pkt 2 + §2.4).
_VERIFICATION_REF = re.compile(
    r"\b(jeg\s+)?(grep'?ede|grepped|tjekkede|checkede|verificerede|bekræftede|"
    r"læste|kørte|so?å|ifølge|jf\.|jvf\.|som\s+det\s+fremgår|outputtet\s+viser|"
    r"loggen\s+viser)\b|§\s*\d|\bse\s+§|linje\s+\d", re.I)

# Tools der direkte verificerer ground truth (spec §2.2 pkt 1).
_VERIFYING_TOOLS: frozenset[str] = frozenset({
    "grep", "read_file", "bash", "search", "find_files", "search_memory",
    "operator_grep", "operator_read_file", "operator_bash", "operator_glob",
    "operator_list_dir", "run_pytest", "verify_file_contains", "service_status",
    "read_brain_entry", "search_jarvis_brain",
})


@dataclass
class DiagnosisResult:
    detected: bool = False
    pattern: str = ""
    claim_snippet: str = ""
    verified: bool = False
    reason: str = ""  # hvorfor verified/exempt


@dataclass
class DiagnosisEvent:
    event_id: str
    timestamp: str
    session_id: str
    run_id: str
    pattern_matched: str
    claim_text: str
    verified: bool
    verification_tool: str = ""
    blocked: bool = False
    extra: dict = field(default_factory=dict)


def analyze_diagnosis(text: str, *, tools_used: list[str] | None = None) -> DiagnosisResult:
    """Ren detektion: er der en uverificeret diagnostisk konklusion i teksten?

    Returnerer DiagnosisResult. detected=False hvis intet diagnostisk mønster (eller
    kun med usikkerheds-signal). verified=True hvis et ground-truth-tool blev kørt
    ELLER teksten refererer en verificering. Ingen sideeffekter.
    """
    t = text or ""
    tools = {str(x).strip() for x in (tools_used or [])}

    match = None
    pat = ""
    for p in _DIAGNOSIS_PATTERNS:
        m = p.search(t)
        if m:
            match, pat = m, p.pattern
            break
    if not match:
        return DiagnosisResult(detected=False)

    # Usikkerheds-signal i nærheden af påstanden → ikke en selvsikker diagnose.
    if _UNCERTAINTY.search(t):
        return DiagnosisResult(detected=False, pattern=pat, reason="uncertainty-signal")

    snippet = t[max(0, match.start() - 40): match.end() + 40].strip()

    # Verificeret hvis et ground-truth-tool blev kørt i runet.
    used_verify = sorted(tools & _VERIFYING_TOOLS)
    if used_verify:
        return DiagnosisResult(detected=True, pattern=pat, claim_snippet=snippet,
                               verified=True, reason=f"verifying-tool:{used_verify[0]}")
    # Eller hvis teksten eksplicit refererer en verificering / kilde.
    if _VERIFICATION_REF.search(t):
        return DiagnosisResult(detected=True, pattern=pat, claim_snippet=snippet,
                               verified=True, reason="verification-reference")

    # Uverificeret diagnostisk konklusion.
    return DiagnosisResult(detected=True, pattern=pat, claim_snippet=snippet,
                           verified=False, reason="unverified")


def diagnosis_gate_enforce(text: str, *, session_id: str = "", run_id: str = "",
                           tools_used: list[str] | None = None) -> str:
    """Pipeline-hook (spec §3.2): kører efter fact-gate, før append_chat_message.

    FASE 1 ADVISORY: logger uverificerede diagnoser men returnerer teksten UÆNDRET
    (blokerer ikke). Fail-open — enhver fejl svælges så gate'en aldrig taber output.
    """
    try:
        res = analyze_diagnosis(text, tools_used=tools_used)
        if res.detected and not res.verified:
            ev = DiagnosisEvent(
                event_id=uuid.uuid4().hex,
                timestamp=datetime.now(timezone.utc).isoformat(),
                session_id=session_id, run_id=run_id,
                pattern_matched=res.pattern, claim_text=res.claim_snippet,
                verified=False, blocked=False,
            )
            logger.warning(
                "diagnosis-gate ADVISORY: uverificeret diagnose run_id=%s session=%s "
                "claim=%r pattern=%r", run_id, session_id, res.claim_snippet, res.pattern,
            )
            try:
                from core.eventbus.bus import event_bus
                event_bus.publish("diagnosis.unverified", {
                    "event_id": ev.event_id, "session_id": session_id, "run_id": run_id,
                    "claim": res.claim_snippet, "pattern": res.pattern,
                })
            except Exception:
                pass
    except Exception:
        pass  # fail-open: gate må aldrig spise output
    return text
