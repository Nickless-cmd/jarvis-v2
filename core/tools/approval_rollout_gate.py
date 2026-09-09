"""Et nyt godkendelses-vaerktoej maa ikke rulles ud foer broen baerer — K4.

Exit-kriteriet: «approval-required tools cannot enter rollout until the
invocation-bound atomic approval bridge is active».

## Hvad det betyder her

At annoncere et vaerktoej til modellen ER dets udrulning. Kraever vaerktoejet
godkendelse, og broen ikke er aktiv, saa hviler godkendelsen paa den gamle
inline-sti: en tilstand i hukommelsen, en UI-besked, og ingen atomisk
overtagelse foer afsendelsen. Den sti er god nok til de vaerktoejer der
allerede lever paa den — men den skal ikke faa flere passagerer.

## Hvorfor der er en liste med navne i

Nitten vaerktoejer kraever godkendelse i dag (maalt 9/9-2026). De blev rullet
ud laenge foer broen fandtes. At blokere dem nu ville tage `bash`, `write_file`
og hele operator-saettet fra Jarvis — en langt stoerre skade end den gaeldspost
de udgoer.

Saa de staar opskrevet. Ikke som en undtagelse der forsvinder i en kommentar,
men som en LISTE man kan taelle: hver gang broen overtager et af dem, bliver
listen kortere, og gaelden er et tal frem for en fornemmelse.

Et NYT navn kommer ikke paa listen. Det er hele pointen.

## Fail-open, men ikke tavst

Kan gaten ikke afgoere noget, annonceres vaerktoejet. En vagt der skjuler
vaerktoejer naar den selv er i stykker, ville vaere vaerre end ingen vagt —
men den siger det hoejt.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Maalt 9/9-2026 med `tool_definition_v2`. Rullet ud FOER broen fandtes.
# Listen maa kun blive KORTERE. Naar broen overtager et vaerktoej, ryger dets
# navn herfra — og gaelden er et tal, ikke en fornemmelse.
GRANDFATHERED: frozenset[str] = frozenset({
    "bash", "edit_file", "write_file", "load_more_tools",
    "operator_bash", "operator_browser_evaluate", "operator_edit_file",
    "operator_kill_process", "operator_launch_app", "operator_open_url",
    "operator_record_audio", "operator_write_file",
    "calendar_create_event", "docs_append", "gmail_send", "sheets_write",
    "phone_adb_screenshot", "phone_adb_shell",
    "stripe_create_issuing_card",
})


def bridge_active() -> bool:
    """Haandhaever godkendelses-broen — eller koerer den stadig i skygge?

    Eksplicit opt-in. Husets `is_enabled` er fail-open og ville paastaa at
    broen baerer, foer nogen har besluttet det.
    """
    try:
        from core.services.central_switches import _key, shared_cache
        v = shared_cache.get(_key("approval", "bridge_enforcing"))
    except Exception:
        return False
    return isinstance(v, dict) and v.get("enabled") is True


def may_advertise(tool_name: str) -> tuple[bool, str]:
    """Maa vaerktoejet annonceres til modellen? (ja/nej, grund)."""
    navn = str(tool_name or "")
    try:
        from core.tools.tool_definition_v2 import APPROVAL_ASK, describe
        d = describe(navn)
        if d is None or d.approval_requirement != APPROVAL_ASK:
            return True, ""
        if navn in GRANDFATHERED:
            return True, "grandfathered"
        if bridge_active():
            return True, "broen er aktiv"
        return False, ("kraever godkendelse, men den invokations-bundne bro er "
                       "ikke aktiv endnu (K4)")
    except Exception:
        # Fail-open: en vagt der skjuler vaerktoejer naar den selv er i stykker,
        # er vaerre end ingen vagt. Men den tier ikke om det.
        logger.warning("approval_rollout_gate: kunne ikke afgoere %s — "
                       "annonceres", navn, exc_info=True)
        return True, "gaten kunne ikke afgoere det"


def blocked() -> list[str]:
    """Hvilke vaerktoejer holdes tilbage lige nu? Tom liste er det normale."""
    from core.tools.tool_definition_v2 import all_definitions
    return sorted(d.name for d in all_definitions()
                  if not may_advertise(d.name)[0])


def debt() -> list[str]:
    """Gaelden: godkendelses-vaerktoejer der lever paa den gamle inline-sti."""
    from core.tools.tool_definition_v2 import APPROVAL_ASK, all_definitions
    return sorted(d.name for d in all_definitions()
                  if d.approval_requirement == APPROVAL_ASK
                  and d.name in GRANDFATHERED)
