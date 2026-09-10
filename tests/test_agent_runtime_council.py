"""Raadet taeller nu sine ture — og sikkerhedsnettene virker der. Fase 6.

«depth, child-count, provider, cost, token, time, tool, secret, and workspace
limits are enforced across failover.»

MAALT 10/9-2026 paa produktionen:

    explore-boern     1,0 runs hver (97 boern) — one-shot som designet
    raadsmedlemmer    8,4 runs i snit, op til TI (91 boern)
    turns_completed   hoejst 1 for ALLE 190

Raadet skaber sine runs DIREKTE med `create_agent_run` og gaar uden om
`execute_agent_task` — hvor `turns_completed_delta=1` er det ENESTE sted i
huset turen taelles. Derfor kunne hverken `max_turns` eller budget-tjekket
nogensinde udloese for netop de agenter der koerer flest gange.

Sikkerhedsnettet fandtes altsaa ikke dér hvor det var noedvendigt. Og det er
det net Bjoern valgte at hvile paa i juli, da budgettet blev sat til
ubegraenset for ikke at kvaele agenter midt i opgaven.
"""
from __future__ import annotations

import inspect

from core.services import agent_runtime_council as C


def test_raadet_taeller_turen():
    kilde = inspect.getsource(C)
    assert "turns_completed_delta=1" in kilde, (
        "raadet taeller stadig ikke sine ture — max_turns kan ikke udloese")


def test_raadet_koerer_BEGGE_graense_tjek():
    kilde = inspect.getsource(C)
    assert "_check_max_turns_and_expire" in kilde
    assert "_check_budget_and_expire" in kilde


def test_tjekkene_ligger_EFTER_at_turen_er_taalt():
    """Ellers ville loftet blive maalt mod et tal der endnu ikke var opdateret,
    og altid vaere én tur bagud."""
    kilde = inspect.getsource(C)
    i_tael = kilde.index("turns_completed_delta=1")
    i_tjek = kilde.index("_check_max_turns_and_expire")
    assert i_tael < i_tjek


def test_et_kollapset_tjek_stopper_ikke_raadet():
    """En debat maa ikke doe fordi et graense-tjek fejlede.

    (Foerste udgave af testen brugte `.index()`, som fandt IMPORT-linjen og
    ikke kaldet — vinduet naaede derfor aldrig frem til vagten. Nu ledes der
    efter selve advarslen, som kun findes ét sted.)
    """
    kilde = inspect.getsource(C)
    assert "raad: kunne ikke koere graense-tjek" in kilde
    i_kald = kilde.rindex("_check_max_turns_and_expire(agent_id)")
    hale = kilde[i_kald:i_kald + 400]
    assert "except Exception" in hale, "graense-tjekket er uden vagt"


def test_budget_tjekket_er_et_NO_OP_for_raadet(isolated_runtime, monkeypatch):
    """Alle 93 raadsmedlemmer har budget 0 = ubegraenset, saa tjekket kan ikke
    kvaele en debat. Det var praecis den fejl der kostede en dag i juli:
    et lille budget gav «completed men tomt».
    """
    from core.runtime.db_agent_runtime import create_agent_registry_entry
    from core.services.agent_runtime_spawn import _check_budget_and_expire

    create_agent_registry_entry(agent_id="raad-1", role="filosof",
                                budget_tokens=0, council_id="c1")
    assert _check_budget_and_expire("raad-1", tokens_used=999_999) is False


def test_tur_loftet_ER_et_aegte_net(isolated_runtime):
    """Det bider ikke i dag — hoejeste maalte er ti runder mod et loft paa 20 —
    men det skal kunne bide."""
    from core.runtime.db_agent_runtime import (
        create_agent_registry_entry, update_agent_registry_entry,
    )
    from core.services.agent_runtime_spawn import _check_max_turns_and_expire

    create_agent_registry_entry(agent_id="raad-2", role="filosof",
                                max_turns=3, council_id="c1")
    update_agent_registry_entry("raad-2", turns_completed_delta=3)
    assert _check_max_turns_and_expire("raad-2") is True


# ── runden koerer nu parallelt, med bevaret raekkefoelge — Fase 6 ────────
#
# MAALT 10/9-2026: 763 raads-runs, 17,4 sekunder i snit, 3,7 medlemmer pr.
# raad. `convene_council` koerer SYNKRONT, saa en runde froes Jarvis' tur i
# omkring et minut.
#
# Den gamle kommentar sagde at raadet var sekventielt for at «preserve
# deliberation order». Men der er ingen deliberation inden i en runde:
# `messages` hentes ÉN gang FOER loekken, og hvert medlem faar samme snapshot.
# Ingen ser hinandens indlaeg fra denne runde. Det sekventielle bevarede kun
# raekkefoelgen af resultater.


def test_transskriptet_hentes_EN_gang_foer_loekken():
    """Grundlaget for at parallelisering er adfaerds-bevarende. Flyttes
    hentningen ind i `_run_one_worker`, ville medlemmerne pludselig se
    hinanden — og saa maa runden ikke koere parallelt laengere."""
    kilde = inspect.getsource(C)
    i_hent = kilde.index("messages = list_agent_messages(")
    i_worker = kilde.index("def _run_one_worker(")
    assert i_hent < i_worker, (
        "transskriptet hentes nu inde i workeren — parallelisering aendrer "
        "hvad medlemmerne ser")


def test_raadet_koerer_PARALLELT():
    kilde = inspect.getsource(C)
    assert 'if mode == "swarm" and len(workers) > 1:' not in kilde
    assert "if len(workers) > 1:" in kilde


def test_raekkefoelgen_er_BEVARET():
    """`as_completed` ville give resultatet i tilfaeldig orden. Rundens output
    fodrer syntesen, saa ordenen skal vaere den samme hver gang.

    Spoerger AST'en, ikke teksten: kommentarerne NAEVNER `as_completed` for at
    forklare hvorfor det ikke bruges, og en tekst-soegning faldt derfor over
    sin egen forklaring.
    """
    import ast
    kilde = inspect.getsource(C)
    assert "for fut in futures:" in kilde
    brugt = any(isinstance(n, ast.Name) and n.id == "as_completed"
                for n in ast.walk(ast.parse(kilde)))
    assert not brugt, "as_completed bruges stadig — raekkefoelgen er tilfaeldig"


def test_en_enkelt_worker_koerer_stadig_uden_traadpulje():
    """Ingen grund til at starte en pulje for ét medlem."""
    kilde = inspect.getsource(C)
    i = kilde.index("if len(workers) > 1:")
    assert "else:" in kilde[i:i + 900]


# ── forkortelsen skal kunne SES — 10/9-2026 ─────────────────────────────
#
# Maalt paa Bjoerns eget raad: de fire medlemmer svarede 1.454, 2.070, 2.494 og
# 2.942 tegn. Hver position blev gemt som PRAECIS 400. Mellem 72% og 86% af
# hver holdning blev smidt vaek, hårdt klippet midt i et ord.
#
# Jarvis laeste resultatet og skrev: «outputtet er afkortet — hver position
# klippet midt i en saetning». Han troede det var et token-artefakt. Det var
# `value[:limit]`.


def test_kort_tekst_roeres_ikke():
    assert C._trim("kun lidt tekst") == "kun lidt tekst"


def test_lang_tekst_SIGER_at_der_mangler_noget():
    """Samme princip som `complete` paa en vaerktoejs-handle: en forkortelse
    der ikke kan ses, laeses som hele svaret."""
    ud = C._trim("ord " * 300)
    assert "tegn udeladt" in ud


def test_den_klipper_ved_en_ORDGRAENSE():
    tekst = "alfa bravo charlie delta echo foxtrot golf hotel india juliet"
    ud = C._trim(tekst, limit=20)
    hoved = ud.split(" […")[0]
    assert tekst.startswith(hoved), "hovedet er ikke et praefiks af originalen"
    assert not hoved.endswith(("c", "h")), "klippet midt i et ord"
    assert " " not in hoved[-1:], "efterlod et haengende mellemrum"


def test_antallet_af_udeladte_tegn_passer():
    tekst = "ord " * 300
    normaliseret = " ".join(tekst.split())
    ud = C._trim(tekst, limit=100)
    hoved = ud.split(" […")[0]
    udeladt = int(ud.split("[…")[1].split(" ")[0])
    assert len(hoved) + udeladt == len(normaliseret)


def test_praecis_paa_graensen_forkortes_ikke():
    tekst = "a" * 400
    assert C._trim(tekst, limit=400) == tekst


def test_et_enkelt_meget_langt_ord_klippes_alligevel():
    """Uden fallback ville hovedet blive tomt og hele positionen forsvinde."""
    ud = C._trim("x" * 900, limit=100)
    assert ud.startswith("x") and "tegn udeladt" in ud
