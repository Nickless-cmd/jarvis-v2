"""Ingen test må skrive i den ægte ~/.jarvis-v2/state/*.json.

Databasen har haft sit værn længe. JSON-state havde intet, og det blev dyrt
17/9-2026: `in_flight_runs.json` i produktionen stod fuld af test-fikstur
(`visible-cap-*`, `session-smoke`, `visible-loop-not-blocked`), fordi enhver
test der kaldte `mark_started` skrev direkte i den ægte fil.

Så længe journalen kun blev LÆST var det rod. Med den varige genoptagelse er
den en KØ: dispatcheren tog to fikstur-poster ved næste genstart og kørte dem
som ægte synlige ture med beskeden «hej» — den ene på den betalte lane.
Testdata blev til rigtige kald.

Testen her er derfor ikke en stil-regel. Den er værnet mod at det sker igen.
"""
from __future__ import annotations

from pathlib import Path

from core.runtime import state_store
from core.services import in_flight_runs


def _aegte_state() -> Path:
    from core.runtime.config import STATE_DIR
    return Path(STATE_DIR)


def test_state_store_peger_IKKE_paa_den_aegte_mappe():
    assert Path(state_store._STATE_DIR) != _aegte_state()


def test_transskript_roden_peger_IKKE_paa_produktionen():
    """Samme fejlform som `state_store` — målt 16/10-2026.

    `agent_transcript` beregnede sin sti ved IMPORT og hardcodede
    ``~/.jarvis-v2``, så skjoldet (der sætter ``JARVIS_HOME``) ikke dækkede den.
    Testfilens cleanup-fixture ryddede derfor PRODUKTIONENS transskripter ved
    hver kørsel — mappen stod tom, sidste tømning 12:55:41.
    """
    from core.services import agent_transcript as at
    aegte = Path("~/.jarvis-v2/state/agent_transcripts").expanduser()
    assert at.transcript_dir() != aegte


def test_agent_transskript_lander_i_skjoldet_og_ikke_i_produktionen():
    """Den konkrete vej transskripterne forsvandt ad.

    Tjekket ligger FOER skrivningen. Målt 16/10-2026 under mutationstesten: med
    ruten pegende på produktionen skrev testen selv et transskript dér og
    efterlod det — så vagten blev selv en forurener. Rækkefølgen er derfor
    ikke kosmetisk.
    """
    from core.services import agent_transcript as at
    aegte_rod = Path("~/.jarvis-v2/state/agent_transcripts").expanduser()
    rod = at.transcript_dir()
    assert rod != aegte_rod, f"transskript-roden peger paa PRODUKTIONEN: {rod}"

    at.write_event("jarvis-shield-proeve", {"kind": "proeve"})
    skrevet = rod / "jarvis-shield-proeve" / "transcript.jsonl"
    assert skrevet.is_file(), "transskriptet blev slet ikke skrevet"


def test_en_journal_post_lander_i_skjoldet_og_ikke_i_produktionen():
    """Den konkrete vej fikstur-posterne kom ind ad."""
    in_flight_runs.mark_started(run_id="visible-shield-proeve", session_id="s-shield",
                                user_message="hej")
    skrevet = Path(state_store._STATE_DIR) / "in_flight_runs.json"
    assert skrevet.is_file(), "posten blev slet ikke skrevet"
    assert "visible-shield-proeve" in skrevet.read_text(encoding="utf-8")

    aegte = _aegte_state() / "in_flight_runs.json"
    if aegte.is_file():
        assert "visible-shield-proeve" not in aegte.read_text(encoding="utf-8")


def test_mcp_token_stien_peger_IKKE_paa_produktionen():
    """Samme fejlform som `state_store` og transskripterne — målt 16/10-2026.

    `mcp_auth` havde sin token-sti som en import-tids-konstant med
    ``~/.jarvis-v2`` hardcodet. Filen bærer OAuth-tokens: en test der skrev
    gennem ``set_token`` uden at overskrive konstanten skrev i produktionens
    token-lager — eller overskrev det. Produktionsfilen var urørt (sidst
    skrevet 9/9), så intet var tabt; fælden var blot åben.
    """
    from core.services import mcp_auth
    aegte = Path("~/.jarvis-v2/config/mcp_tokens.json").expanduser()
    assert mcp_auth.tokens_path() != aegte


def test_mcp_token_lander_i_skjoldet_og_lader_produktionen_vaere():
    """Tjekket ligger FOER skrivningen — lært af transskript-vagten 16/10-2026.

    Med ruten pegende på produktionen skrev den vagt selv i produktionen og
    efterlod et spor. Rækkefølgen er derfor ikke kosmetisk.
    """
    from core.services import mcp_auth
    aegte = Path("~/.jarvis-v2/config/mcp_tokens.json").expanduser()
    sti = mcp_auth.tokens_path()
    assert sti != aegte, f"token-stien peger paa PRODUKTIONEN: {sti}"

    foer = aegte.read_bytes() if aegte.is_file() else None
    mcp_auth.set_token("jarvis-shield-proeve", access_token="ikke-en-hemmelighed")
    assert sti.is_file(), "token-filen blev slet ikke skrevet"
    if foer is not None:
        assert aegte.read_bytes() == foer, "produktionens token-fil blev aendret"
