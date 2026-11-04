"""En agent der melder «jeg kan ikke løse opgaven» er ikke en succes (4/11-2026).

MAALT 4/11-2026 i `agent_runs` (7 dage, status='completed', n=4):

  * alle 4 havde et svar der erklaerede at opgaven ikke kunne loeses
  * alle 4 stod som `completed` med `error_code=''` og `error_phase=''`

Den skarpeste: `agent-71b2452a7d0e42e79395f4a38d3109e7` svarede ordret
«Jeg kan ikke loese opgaven: mit vaerktoejssaet i denne sandbox indeholder
ikke ...» — og blev stemplet `completed`, `provider_status=completed`,
`tool_calls=1`. Den HAVDE `wt_bash` og `wt_write_file`. Der findes altsaa
INTET strukturelt signal at laese: agent-loekken rapporterede selv succes,
og vaerktoejskaldet blev foretaget. Markoeren maa vaere en erklaering.

HVORFOR EN EGEN KODE OG EN EGEN STATUS
`AGENT_INCOMPLETE`/`delivery` (26/10) betyder «agenten blev afbrudt midt i».
Det er en anden jagt end «agenten vurderede at den ikke kunne». Slaas de
sammen, kan den naeste mig ikke se forskel. Status er derfor `declined`,
ikke `failed`: agenten LEVEREDE et svar, og arbejdet skal bevares — en
`failed`-status ville kaste leverancen vaek for at faa signalet.

BEMAERK om testens egen faelde: `db_agent_runtime` importerer `connect` ved
import-tid, saa en monkeypatch paa `DB_PATH` rammer ingen ting. Testen
patcher derfor det symbol funktionen faktisk kalder (samme greb som
`test_agent_run_raekken_baerer_fasen.py`).
"""

from __future__ import annotations

import sqlite3

import pytest

# De fire faktiske tekster fra `agent_runs` 4/11-2026, forkortet til det
# afgoerende. De er malet, ikke opfundet.
FAKTISKE = {
    "agent-71b2": (
        "Jeg kan ikke løse opgaven: mit værktøjssæt i denne sandbox indeholder "
        "kun `wt_bash`, `wt_write_file` og `agent_note` — der findes intet "
        "`restart_self`-værktøj jeg kan kalde."
    ),
    "agent-c377": (
        "**Summary** — Jeg kan ikke løse opgaven: `restart_self` er ikke et af "
        "mine tilgængelige værktøjer, og jeg kan ikke bruge `wt_bash`."
    ),
    "agent-2a53": (
        "**Summary** — Jeg kan ikke løse opgaven, fordi `restart_self` ikke "
        "findes blandt mine tildelte værktøjer. **Findings** — De eneste …"
    ),
    "agent-0cfb": (
        "**Summary** — Jeg kan ikke løse opgaven. Opgaven kræver et kald til "
        "værktøjet `restart_self`, men det findes ikke i mit tildelte …"
    ),
}

# Svar der IKKE maa rammes: agenten arbejdede og leverede.
NORMALE = {
    "loest": "Jeg har rettet fejlen i `continuity.py` og kørt de 21 tests — alle grønne.",
    "rapport": "**Summary** — Jeg læste 4 filer og fandt at guarden aldrig blev kaldt.",
    "delvist_men_loest": (
        "Jeg kunne ikke løse det med `restart_self`, men fandt en anden vej "
        "gennem `systemctl` og fik tjenesten genstartet."
    ),
    "naevner_manglende_vaerktoej": (
        "**Findings** — `restart_self` findes ikke i mit værktøjssæt, så jeg "
        "brugte `wt_bash` i stedet. Det virkede."
    ),
    "tom": "",
    "hilsen": "Klar til næste opgave.",
}


def _frisk_db(tmp_path, monkeypatch):
    """En rigtig sqlite-fil, koblet paa det `connect` funktionen kalder."""
    from core.runtime import db_agent_runtime as rt

    sti = tmp_path / "agent_runs.db"

    def _connect():
        c = sqlite3.connect(sti)
        c.row_factory = sqlite3.Row
        return c

    monkeypatch.setattr(rt, "connect", _connect, raising=False)
    with _connect() as c:
        rt._ensure_agent_runtime_tables(c)
        c.execute(
            "INSERT INTO agent_runs (run_id, agent_id, status, created_at, updated_at,"
            " output_summary, error_code, error_phase, artifact_path)"
            " VALUES ('run-d','agent-d','running','t0','t0','','','','/tmp/art.txt')"
        )
        c.commit()
    return sti


def _raekke(sti):
    conn = sqlite3.connect(sti)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM agent_runs WHERE run_id='run-d'").fetchone()
    conn.close()
    return dict(r)


# ── (a) erklaeringen fanges ────────────────────────────────────────────


@pytest.mark.parametrize("navn,tekst", sorted(FAKTISKE.items()))
def test_en_erklaering_om_at_opgaven_ikke_kunne_loeses_fanges(navn, tekst):
    from core.runtime.db_agent_contract import decline_error

    kode, fase = decline_error(text=tekst)
    assert (kode, fase) == ("AGENT_DECLINED", "capability"), f"{navn} fik {(kode, fase)!r}"


# ── (b) den anden kant: normalt arbejde maa ikke rammes ────────────────


@pytest.mark.parametrize("navn,tekst", sorted(NORMALE.items()))
def test_normalt_arbejde_klassificeres_ikke(navn, tekst):
    from core.runtime.db_agent_contract import decline_error

    kode, fase = decline_error(text=tekst)
    assert (kode, fase) == ("", ""), f"{navn} blev fejlagtigt stemplet {(kode, fase)!r}"


def test_en_der_naevner_et_manglende_vaerktoej_men_arbejder_er_ikke_declined():
    """Den BREDE markoer — «enhver der naevner et vaerktoej den ikke har» —
    ville ramme denne. Den loeste opgaven og skal blive completed."""
    from core.runtime.db_agent_contract import decline_error

    tekst = (
        "Jeg havde ikke `restart_self`, så jeg kaldte `wt_bash` og kørte "
        "systemctl direkte. Tjenesten er genstartet, uptime 16:47."
    )
    assert decline_error(text=tekst) == ("", "")


def test_erklaeringen_skal_staa_tidligt_i_svaret():
    """En agent der RAPPORTERER om en anden agents erklaering er ikke selv declined."""
    from core.runtime.db_agent_contract import decline_error

    tekst = (
        "Jeg har gennemgået de fire kørsler. "
        + "Fyld. " * 60
        + "Til sidst: den ene agent skrev «jeg kan ikke løse opgaven», hvilket er fejlen."
    )
    assert decline_error(text=tekst) == ("", "")


# ── (c) arbejdet bevares ───────────────────────────────────────────────


def test_declined_bevarer_leverancen(tmp_path, monkeypatch):
    """Status maa ikke vaere `failed`: agenten LEVEREDE et svar, og baade
    summary og artifact skal staa der bagefter."""
    sti = _frisk_db(tmp_path, monkeypatch)
    from core.runtime.db_agent_runtime import update_agent_run

    update_agent_run(
        "run-d",
        status="declined",
        output_summary="Jeg kan ikke løse opgaven: værktøjet findes ikke.",
        error_code="AGENT_DECLINED",
        error_phase="capability",
    )
    r = _raekke(sti)
    assert r["status"] == "declined", f"fik {r['status']!r}"
    assert r["error_code"] == "AGENT_DECLINED"
    assert r["error_phase"] == "capability"
    assert "kan ikke løse" in r["output_summary"], "leverancen blev kastet væk"
    assert r["artifact_path"] == "/tmp/art.txt", "artifact-stien blev nulstillet"


# ── montering: spawn skal kalde den, ikke hardkode completed ───────────


def test_spawn_succes_stien_kalder_klassificeringen():
    """Adfaerdstesten ovenfor beviser klassificeringen. Denne beviser at den
    bliver BRUGT — en korrekt funktion ingen kalder er dagens fejlform.

    Vagten er strukturel (inspect), samme form som husets egen
    `test_porten_var_bygget_men_aldrig_aabnet`. Den fanger fjernelse af
    kaldet, ikke en aendret raekkefoelge.
    """
    import inspect

    from core.services import agent_runtime_spawn as M

    src = inspect.getsource(M)
    assert "decline_error" in src, "spawn kalder ikke klassificeringen — den er doed kode"
    assert 'status="declined"' not in src, (
        "status skal komme fra klassificeringen, ikke staa hardkodet"
    )
