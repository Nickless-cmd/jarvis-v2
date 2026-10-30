"""CANDIDATE-penaltyen må kun ramme chunks hvor markøren ER indholdet.

Målt 28/10-2026 slut-til-slut: `search_memory()` gangede scoren med 0,3 for
ethvert chunk hvis tekst blot INDEHOLDt ``[CANDIDATE→``. Daily-notes bærer
markøren som ``carried:``-metadata midt i en ellers værdifuld entry — 2182 af
2451 daily-chunks (89 %) blev derfor demoteret under ``adjusted_scores <= 0.1``
og kunne aldrig surface, uanset hvor godt de matchede.

Probe der afslørede det: en næsten ordret streng fra
``memory/daily/2026-10-18.md`` («39 åbne jarvis.db-håndtag mod 29 registrerede
poster») scorer raw cosine 0,763 — rank #0 af 12.696 chunks — men var
FRAVÆRENDE fra top-8; semantisk fjerne imported-claude-mem-filer vandt i
stedet.

Disse tests værner om skelnen, ikke om tallet: en carried-metadata-chunk må
ikke straffes, og en ægte candidate-chunk skal stadig.
"""
from __future__ import annotations

from core.services.memory_search import _candidate_er_primaer, _chunk_markdown


def test_carried_metadata_straffes_ikke():
    """Daily-formen: markøren står som `carried:`-metadata i slutningen."""
    tekst = (
        "2026-10-18T04:47:31.303860+00:00: - user: Tag den gap nu "
        "- assistant: Taget. Gabet er forklaret — og det er ikke en laekage. "
        "**Gabet: 39 aabne jarvis.db-haandtag mod 29 registrerede poster i api'et.** "
        "Tre kilder, og kun den foerste er egentlig interessant. "
        "- carried: - [CANDIDATE→REQUEST] Undersoeg gap i jarvis.db-haandtag "
        "- [CANDIDATE→MEMORY.md] jarvis.db-haandtags-gab er kosmetisk bogfoering"
    )
    assert _candidate_er_primaer(tekst) is False, (
        "en daily-chunk der baerer markoeren som carried-metadata blev straffet "
        "— det er praecis den fejl der gjorde 89 % af daily usoegelige"
    )


def test_aegte_candidate_chunk_straffes_stadig():
    """Den oprindelige hensigt: en chunk der ER en candidate-hint."""
    assert _candidate_er_primaer("[CANDIDATE→MEMORY.md] et uadopteret forslag") is True


def test_aegte_candidate_efter_sti_praefiks_straffes():
    """`_chunk_markdown` saetter stien foran kroppen — det maa ikke skjule den."""
    assert _candidate_er_primaer("MEMORY.md › Aabne traade: [CANDIDATE→MEMORY.md] forslag") is True


def test_markering_midt_i_prosa_er_ikke_primaer():
    """Staar der rigtig tekst foer markoeren, er den ikke chunkens indhold."""
    assert _candidate_er_primaer("Lang udredning om fd-laekagen [CANDIDATE→X] og mere") is False


def test_uden_markoer_er_svaret_falsk():
    assert _candidate_er_primaer("helt almindelig tekst uden markoer") is False


def test_den_faktiske_daily_form_klassificeres_korrekt():
    """Slut-til-slut paa den fil probe-queryet kom fra.

    Kravet er ikke «nul markoerer» — det er at INGEN af dem er chunkens
    primaere indhold. Maalt 28/10-2026: 119 af 130 chunks bar markoeren, og
    alle 119 er metadata.
    """
    import pathlib

    fil = pathlib.Path(
        "/home/bs/.jarvis-v2/workspaces/bjorn/memory/daily/2026-10-18.md"
    )
    if not fil.exists():
        import pytest

        pytest.skip("daily-filen findes ikke i dette miljoe")

    chunks = _chunk_markdown(fil.read_text(encoding="utf-8"), "memory/daily/2026-10-18.md")
    med_markoer = [c for c in chunks if "[CANDIDATE→" in c.text]
    assert med_markoer, "filen skulle baere markoerer — ellers maaler testen ingenting"
    primaere = [c for c in med_markoer if _candidate_er_primaer(c.text)]
    assert primaere == [], (
        f"{len(primaere)} af {len(med_markoer)} daily-chunks blev klassificeret som "
        f"primaere — de er carried-metadata og maa ikke demoteres"
    )
