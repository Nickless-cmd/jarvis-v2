"""TTFT og tok/s — målt hos os (Bjørn 4/10-2026).

Testene måler de VALG der blev truffet, ikke bare at der kommer et tal ud:
at tænke-tokens tæller med, at nævneren er skrivetiden og ikke hele turen, og
at «ikke målt» er sin egen tilstand frem for et nul.
"""
from __future__ import annotations

import pytest

from core.services import svar_tempo


@pytest.fixture(autouse=True)
def rent_lager():
    svar_tempo._tempi.clear()
    yield
    svar_tempo._tempi.clear()


def _ur(start: float, foerste: float | None, nu: float, monkeypatch):
    """Sæt et fast ur. `time.monotonic` kan ikke mockes med en konstant —
    modulet kalder den både ved start og ved afslutning, så den skal give
    forskellige svar i rækkefølge."""
    svar: list[float] = [start] + ([foerste] if foerste is not None else []) + [nu]
    it = iter(svar)
    monkeypatch.setattr(svar_tempo.time, "monotonic", lambda: next(it))


def test_ttft_er_tiden_til_FOERSTE_token(monkeypatch):
    _ur(10.0, 10.8, 15.0, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    r = svar_tempo.afslut("r", output_tokens=100)
    assert r["ttft_ms"] == 800.0


def test_tok_per_sek_maales_fra_foerste_token_IKKE_fra_turens_start(monkeypatch):
    """Tog TTFT'en 10 af 12 sekunder, er skrivehastigheden de to. Divideres
    der med 12, straffes modellen for en ventetid den allerede er målt på."""
    _ur(0.0, 10.0, 12.0, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    r = svar_tempo.afslut("r", output_tokens=100)
    assert r["ttft_ms"] == 10_000.0
    assert r["tok_per_sek"] == 50.0      # 100 / 2 s — ikke 100/12 = 8,3


def test_foerste_token_er_IDEMPOTENT(monkeypatch):
    """Kalderen står i en delta-løkke og kan ikke selv vide om den er først.
    Skulle den det, ville hver kalder have sin egen `if første`."""
    _ur(0.0, 1.0, 5.0, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    svar_tempo.foerste_token("r")   # maa ikke flytte uret
    svar_tempo.foerste_token("r")
    assert svar_tempo.afslut("r", output_tokens=10)["ttft_ms"] == 1000.0


def test_uden_et_eneste_token_er_begge_tal_UKENDTE(monkeypatch):
    """`None`, ikke 0: et nul ville tegne «TTFT 0ms» i composeren og se ud som
    et måleresultat."""
    _ur(0.0, None, 5.0, monkeypatch)
    svar_tempo.start("r")
    r = svar_tempo.afslut("r", output_tokens=0)
    assert r == {"ttft_ms": None, "tok_per_sek": None}


def test_et_ukendt_run_svarer_ukendt_og_kaster_ikke():
    assert svar_tempo.afslut("findes-ikke") == {"ttft_ms": None, "tok_per_sek": None}


def test_nul_output_tokens_giver_ingen_hastighed(monkeypatch):
    _ur(0.0, 1.0, 5.0, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    r = svar_tempo.afslut("r", output_tokens=0)
    assert r["ttft_ms"] == 1000.0
    assert r["tok_per_sek"] is None


def test_en_skrivetid_paa_naesten_nul_giver_INGEN_hastighed(monkeypatch):
    """Ét token der ankom samtidig med at turen sluttede ville ellers give
    «4000 tok/s» — et tal der ser ud som en måling og ikke er det."""
    _ur(0.0, 1.0, 1.01, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    assert svar_tempo.afslut("r", output_tokens=40)["tok_per_sek"] is None


def test_maalingen_fjernes_naar_den_aflaeses(monkeypatch):
    """Ellers ville et langt levende run samle målinger op til loftet."""
    _ur(0.0, 1.0, 2.0, monkeypatch)
    svar_tempo.start("r")
    svar_tempo.foerste_token("r")
    svar_tempo.afslut("r", output_tokens=10)
    assert "r" not in svar_tempo._tempi


def test_loftet_holder_hukommelsen_i_ro():
    """Et run der aldrig når sin slutning må ikke blive en lækage."""
    for i in range(svar_tempo._MAKS + 20):
        svar_tempo.start(f"r{i}")
    assert len(svar_tempo._tempi) <= svar_tempo._MAKS


def test_tomt_run_id_roerer_intet():
    svar_tempo.start("")
    svar_tempo.foerste_token("")
    assert svar_tempo._tempi == {}


def test_glem_smider_maalingen_vaek():
    svar_tempo.start("r")
    svar_tempo.glem("r")
    assert svar_tempo.afslut("r") == {"ttft_ms": None, "tok_per_sek": None}


# ── Hændelsen og klienten ──────────────────────────────────────────────────

def test_message_delta_UDELADER_tallene_naar_de_ikke_er_maalt():
    """En klient skal kunne skelne «ikke målt» fra «målt til nul» uden at
    kende vores default. Derfor udeladt frem for 0."""
    import json

    from apps.api.jarvis_api.sse_v2_events import MessageDelta
    linje = MessageDelta(stop_reason="end_turn").to_sse_line().strip().splitlines()[-1]
    usage = json.loads(linje[6:])["usage"]
    assert "ttft_ms" not in usage and "tok_per_sek" not in usage


def test_message_delta_baerer_tallene_naar_de_ER_maalt():
    import json

    from apps.api.jarvis_api.sse_v2_events import MessageDelta
    linje = MessageDelta(stop_reason="end_turn", output_tokens=100,
                         ttft_ms=812.4, tok_per_sek=38.2
                         ).to_sse_line().strip().splitlines()[-1]
    usage = json.loads(linje[6:])["usage"]
    assert usage["ttft_ms"] == 812.4
    assert usage["tok_per_sek"] == 38.2


def test_taenke_tokens_taeller_MED_som_foerste_indhold():
    """Kilde-vagt. `reasoning_delta` skal markere TTFT sammen med `delta`:
    tænke-tokens er det første man ser, og en TTFT der sprang dem over ville
    sige 14 s om noget der føltes som 2.

    AST frem for grep: begge navne står også i kommentarer og docstrings i den
    fil, så en streng-søgning ville bestå uden at reglen var der.
    """
    import ast
    import pathlib

    traeet = ast.parse(pathlib.Path("core/services/visible_runs_sse_v2.py").read_text())
    fundet = False
    for node in ast.walk(traeet):
        if not isinstance(node, ast.If):
            continue
        kilde = ast.unparse(node.test)
        if "event_name" not in kilde or "foerste_token" not in ast.unparse(node):
            continue
        assert "reasoning_delta" in kilde and "'delta'" in kilde, (
            f"TTFT-markeringen daekker ikke begge indholds-events: {kilde}")
        fundet = True
    assert fundet, "fandt ingen TTFT-markering i sse_v2"


def test_uret_startes_IKKE_naar_vi_attacher_til_et_levende_run():
    """Kilde-vagt. Ved `_attached` kører runnet allerede — måltes der fra
    dette kald, ville TTFT'en se ud som om modellen var hurtig, fordi den
    havde arbejdet i forvejen."""
    import ast
    import pathlib

    sti = "apps/api/jarvis_api/routes/chat_stream_v2.py"
    traeet = ast.parse(pathlib.Path(sti).read_text())
    # `ast.walk` giver OGSAA foraeldre-noder: den ydre
    # `if settings.server_authoritative_runs:` indeholder ogsaa kaldet. Min
    # foerste udgave tog den foerste traeffer og maalte derfor den forkerte
    # betingelse. Vi samler alle og kraever at ÉN af dem er den rigtige.
    betingelser = [
        ast.unparse(n.test) for n in ast.walk(traeet)
        if isinstance(n, ast.If) and "svar_tempo.start" in ast.unparse(n)
    ]
    assert betingelser, "fandt intet kald til svar_tempo.start i ruten"
    assert "not _attached" in betingelser, (
        f"uret startes ikke bag `not _attached`; fandt {betingelser}")
