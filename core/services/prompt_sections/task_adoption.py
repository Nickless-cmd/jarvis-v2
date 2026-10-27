"""Den korte, faste pegepind til agent-kontraktens ene oprettelsesvej.

Den lange orkestreringskontrakt bor i ``agent_orchestration``. Denne sektion
ligger tidligere i den synlige prompt og skal kun forhindre, at Jarvis falder
tilbage til manuelle filkald ved brede undersoegelser. Den maa derfor aldrig
navngive legacy-spawnere eller opfinde en parallel livscyklus.
"""
from __future__ import annotations


def task_adoption_hint() -> str:
    """Returner en kompakt Task-pegepind, eller tom tekst naar motoren er slukket."""
    try:
        from core.services.agent_contract_service import capability_enabled

        if not capability_enabled():
            return ""
    except Exception:  # Fail closed: en ukendt kontrakttilstand maa ikke annoncere Task.
        return ""
    return (
        "Kraever svaret en afgraenset undersoegelse paa tvaers af flere filer, "
        "saa delegér den med `Task` og subagent_type `researcher`; fortsaet selv, "
        "mens den arbejder. Skal en agent skrive kode, brug samme `Task`-vej med "
        "subagent_type `executor`. Brug ingen legacy-spawnere. Ved du allerede "
        "hvilken fil det er, saa laes eller ret den selv."
    )
