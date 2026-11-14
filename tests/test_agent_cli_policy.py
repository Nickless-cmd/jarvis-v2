"""Rollernes `default_tool_policy` skal give det tabellen lover — på BEGGE veje.

Maalt 10/11-2026. Fejlen havde to lag, og det foerste var det vaerste:

1. **Worker-vejen (aegte fejl, rettet):** `critic` og `planner` var deklareret
   med `"none"` = nul værktøjer. `tools_for_policy("none")` returnerer `[]`,
   saa en critic koert gennem den almindelige agent-worker ikke kunne laese
   noget — den skulle kritisere kode den ikke maatte se. Det var ikke en
   hypotese: jeg valgte `critic` til en maaleopgave ud fra tabellen og fik en
   agent der ikke kunne maale. Den svarede aerligt «jeg har ikke maalt noget»
   — men valget var mit, og det byggede paa en tabel der ikke passede.

2. **CLI-vejen (rettet 14/11-2026):** `_command` satte værktøjerne ud fra ÉN
   ting — om policyen var `worktree-write`. Alt andet fik `Read,Glob,Grep`, saa
   `default_tool_policy` var død kode der. Det er nu en eksplicit mapping
   (`_cli_tools_for_policy`) i stedet for en tavs ternaer.

   Indtil 14/11-2026 gav ingen policy shell. `dec_6a234cd30460` (Bjoern,
   5/11-2026) blev laest som et forbud, og `test_cli_afviger_fra_tabellen_paa_shell`
   fæstnede det. Prisen blev maalt: to agenter afleverede kode uden at koere
   én test, og en tredje skrev 19 filer med typecheck-fejl i baade desk og
   mobil. En skrivende agent uden shell kan ikke verificere sit eget arbejde.

   Bjoern ophaevede det 14/11-2026 («giv claude wt_bash») efter at flagene var
   maalt: `--tools …Bash` + `--restricted` koerer kommandoen, fordi
   `--restricted` kun fjerner Bash naar `--tools` ikke naevner det. Skrivende
   ruter har den nu; laesende har den ikke, og dét fæstnes af
   `test_skrivende_rute_har_shell_og_laesende_har_ikke`.
"""
from __future__ import annotations

import pytest

from core.services import agent_cli_backend as backend
from core.services.agent_runtime_base import AGENT_ROLE_TEMPLATES, tools_for_policy


def _cli_tools(policy: str) -> set[str]:
    return {t.strip() for t in backend._cli_tools_for_policy(policy).split(",") if t.strip()}


# ── worker-vejen: her var fejlen aegte ────────────────────────────────────

@pytest.mark.parametrize("rolle", ["critic", "planner", "researcher"])
def test_vurderende_roller_kan_faktisk_laese(rolle):
    """`tools_for_policy` er hvad worker-agenten faar i haanden.

    Stod rollen med `"none"`, gav den nul værktøjer — og en agent der skal
    vurdere eller planlaegge MOD koden kunne ikke se den.
    """
    policy = str(AGENT_ROLE_TEMPLATES[rolle].get("default_tool_policy") or "")
    navne = tools_for_policy(policy)
    assert navne, f"{rolle} har policy {policy!r} der giver NUL værktøjer"
    assert "read_file" in navne, f"{rolle} kan ikke laese filer (policy {policy!r})"


def test_syntese_og_djaevel_er_bevidst_uden_vaerktoejer():
    """De faar deres input i prompten — det er ikke den samme fejl.

    Vagten skal kunne skelne «deklareret blind med vilje» fra «deklareret
    blind ved en fejl», ellers kan den ikke fange den naeste.
    """
    for rolle in ("synthesizer", "devils_advocate"):
        policy = str(AGENT_ROLE_TEMPLATES[rolle].get("default_tool_policy") or "")
        assert policy == "none", f"{rolle} er aendret til {policy!r} — er det meningen?"
        assert tools_for_policy(policy) == []


# ── CLI-vejen: eksplicit, ikke rettet ─────────────────────────────────────

def test_skrivende_policy_faar_skrivevaerktoejer():
    assert {"Read", "Glob", "Grep", "Edit", "Write"} <= _cli_tools("worktree-write")


def test_laesende_policy_faar_laesevaerktoejer():
    assert {"Read", "Glob", "Grep"} <= _cli_tools("read-only-runtime")


@pytest.mark.parametrize("policy", ["none", "", "ukendt-policy", "read-only-workstation", "can-spawn"])
def test_ingen_cli_policy_goer_agenten_blind(policy):
    """En CLI uden værktøjer kan ikke engang laese filen den skal vurdere.

    Fejlen ville se ud som en tom leverance, ikke som en manglende evne.
    """
    assert _cli_tools(policy), f"policy {policy!r} gav nul værktøjer"


def test_skrivende_rute_har_shell_og_laesende_har_ikke():
    """Shell-fordelingen mellem de to slags ruter — fæstnet, saa den ikke glider.

    Historik, fordi den er dyr: indtil 14/11-2026 gav INGEN policy shell, og
    denne vagt fæstnede netop det. Prisen var maalt — to agenter afleverede
    kode uden at koere én test, og en tredje skrev 19 filer med typecheck-fejl
    som ingen kunne se. En skrivende agent uden shell kan ikke verificere sit
    eget arbejde.

    Bjoern ophaevede begraensningen 14/11-2026 («giv claude wt_bash»), efter
    at flagkombinationen var maalt: `--tools …Bash` + `--restricted` koerer
    kommandoen. `--restricted` fjerner Bash KUN naar `--tools` ikke naevner det.

    Laesende ruter faar den fortsat ikke — en researcher eller critic skal
    undersoege, ikke mutere. Fejler denne test, er fordelingen aendret, og saa
    skal det besluttes eksplicit frem for at glide.
    """
    tabel = set(tools_for_policy("read-only-runtime"))
    assert "bash" in tabel, "tabellen lover ikke laengere shell — opdatér denne vagt"

    assert "Bash" in _cli_tools("worktree-write"), (
        "den skrivende rute mistede shell — saa kan dens agent ikke koere de "
        "tests den selv skrev, og dens «faerdig» daekker kun over at den skrev noget"
    )
    for policy in ("none", "read-only-runtime", "read-only-workstation", "can-spawn"):
        assert "Bash" not in _cli_tools(policy), (
            f"CLI-ruten giver nu shell for laesende policy {policy!r}. Det er en "
            "ny egenskab ved backenden — afgoer eksplicit om den skal have det."
        )


def test_command_sender_policyens_vaerktoejer_til_cli():
    cmd = backend._command(
        "claude-cli", "/usr/bin/claude", "default", "/tmp", "opgave",
        policy="worktree-write", output_path="/tmp/out.txt",
    )
    assert cmd[cmd.index("--tools") + 1] == "Read,Glob,Grep,Edit,Write,Bash"

    cmd_ro = backend._command(
        "claude-cli", "/usr/bin/claude", "default", "/tmp", "opgave",
        policy="read-only-runtime", output_path="/tmp/out.txt",
    )
    assert cmd_ro[cmd_ro.index("--tools") + 1] == "Read,Glob,Grep"


def test_codex_sandbox_foelger_policy():
    skriv = backend._command(
        "codex-cli", "/usr/bin/codex", "default", "/tmp", "opgave",
        policy="worktree-write", output_path="/tmp/out.txt",
    )
    laes = backend._command(
        "codex-cli", "/usr/bin/codex", "default", "/tmp", "opgave",
        policy="read-only-runtime", output_path="/tmp/out.txt",
    )
    assert skriv[skriv.index("--sandbox") + 1] == "workspace-write"
    assert laes[laes.index("--sandbox") + 1] == "read-only"


# ── facaden: listen skal tale om RUTEN, ikke kun politikken ────────────────

def test_facaden_lover_ikke_wt_vaerktoejer_paa_en_cli_rute():
    """Målt 14/11-2026: to agenter fik `wt_bash` annonceret og havde den ikke.

    `asg-dc669ecaebd54825` (claude-cli) svarede «wt_bash findes ikke her» og kørte
    nul tests. `asg-f32b7d7f86a940fc` (codex-cli) skrev 19 filer uden ét testkald.
    Listen afgør både hvad agenten får at vide OG hvad der afvises ved dispatch —
    lover den et værktøj ruten ikke har, koster det en hel kørsel.
    """
    from core.services.agent_task_facade import _annoncerede_vaerktoejer

    worker = _annoncerede_vaerktoejer("worktree-write", "deepseek", True)
    assert "wt_bash" in worker, "worker-ruten HAR wt_bash — den skal stadig annonceres"

    for rute in ("claude-cli", "codex-cli"):
        cli = _annoncerede_vaerktoejer("worktree-write", rute, True)
        assert not [t for t in cli if t.startswith("wt_")], (
            f"{rute} annoncerer wt_-værktøjer den ikke har: {cli}"
        )
        assert "read_file" in cli, "CLI-agenten skal stadig kunne læse filer"


def test_facaden_afviser_ved_bestilling_naar_cli_ruten_mangler_shell():
    """Afvisningen skal nævne at CLI-ruten ikke har shell — ikke kun mangle navnet."""
    from core.services.agent_task_requirements import ufuldstaendige_vaerktoejer
    from core.services.agent_task_facade import _annoncerede_vaerktoejer

    cli = _annoncerede_vaerktoejer("worktree-write", "codex-cli", True)
    mangler = ufuldstaendige_vaerktoejer("kør `wt_bash` og rapportér", cli, set(cli) | {"wt_bash"})
    assert mangler == ["wt_bash"], "facaden skal opdage at wt_bash ikke findes på ruten"
