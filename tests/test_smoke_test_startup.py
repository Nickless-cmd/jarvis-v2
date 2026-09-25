"""Opstarts-røgprøven skal AFVISE. Den har aldrig haft en test.

Den findes for at fange den klasse fejl der sætter jarvis-runtime i en
systemd-genstartsløkke: en TypeError i lifespan, en manglende kolonne, en
import der knækker. Men ingen havde nogensinde set den FEJLE, så vi vidste
ikke om den ville sige fra — kun at den plejede at sige ja.

Selve opstarten køres ikke her (den importerer hele appen og tager
sekunder). Det der pinnes, er kontrakten: hvilken exit-kode hvilken udgang
giver. Det er den kontrakt hooken og CI læser.
"""
import asyncio

import scripts.smoke_test_startup as s


def test_ren_opstart_giver_nul(monkeypatch, capsys):
    async def _ok():
        return None
    monkeypatch.setattr(s, "_run_lifespan", _ok)
    assert s.main() == 0
    assert "OK" in capsys.readouterr().out


def test_en_fejl_i_lifespan_giver_en(monkeypatch, capsys):
    """Præcis den klasse fejl vagten findes for."""
    async def _knaek():
        raise TypeError("uventet kwarg i en daemon-init")
    monkeypatch.setattr(s, "_run_lifespan", _knaek)
    assert s.main() == 1
    ud = capsys.readouterr()
    assert "FAILED" in ud.err
    assert "uventet kwarg" in ud.err        # traceback'et skal med, ikke kun et tal


def test_en_haengende_opstart_giver_to(monkeypatch, capsys):
    """En opstart der hænger er IKKE det samme som en der fejler.

    To forskellige koder, fordi de kræver to forskellige undersøgelser: en
    fejl har et stakspor, et hæng har ingenting og skal findes med et ur.
    """
    async def _haenger():
        await asyncio.sleep(3600)
    monkeypatch.setattr(s, "_run_lifespan", _haenger)
    monkeypatch.setattr(s, "_TIMEOUT_SECONDS", 0.05)
    assert s.main() == 2
    assert "TIMEOUT" in capsys.readouterr().err


def test_tidsgraensen_er_ikke_uendelig():
    """En røgprøve uden loft ville hænge CI i stedet for at melde hæng."""
    assert 0 < s._TIMEOUT_SECONDS <= 300


# ── Bagstopperen (25/9-2026) ─────────────────────────────────────────────────
#
# `test_en_haengende_opstart_giver_to` ovenfor simulerer et haeng med
# `await asyncio.sleep(3600)`. Det er et AWAITABLE haeng, og netop derfor kunne
# `asyncio.wait_for` afbryde det. Men den fejl vagten findes for — et opstart
# der haenger — er overvejende SYNKRON: importer, `create_app()`, DB-kald.
# Loekken naar aldrig at give slip, og `wait_for` fyrer ikke.
#
# Maalt paa `9878c2915` med `_TIMEOUT_SECONDS = 0.4`: skriptet svarede
# «OK in 6.9s». Exit-kode 2 var uopnaaelig for den slags haeng den beskriver.
# Testen ovenfor var groen hele tiden, fordi den maalte den nemme halvdel.

import time


def test_et_SYNKRONT_haeng_fanges_af_bagstopperen(monkeypatch):
    """Den halvdel `wait_for` ikke kan se."""
    ramt: list[int] = []
    monkeypatch.setattr(s, "_AFSLUT", ramt.append)
    monkeypatch.setattr(s, "_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(s, "_BAGSTOP_MARGIN_S", 0.05)

    async def _blokerer_synkront():
        # `time.sleep`, IKKE `asyncio.sleep`: loekken kan ikke give slip, saa
        # `wait_for` er magtesloes. Blokeringen slipper naar bagstopperen har
        # fyret — ellers ville testen selv haenge.
        frist = time.monotonic() + 5.0
        while time.monotonic() < frist and not ramt:
            time.sleep(0.01)

    monkeypatch.setattr(s, "_run_lifespan", _blokerer_synkront)
    s.main()

    assert ramt == [2], "bagstopperen afsluttede ikke med kode 2"


def test_bagstopperen_fyrer_EFTER_wait_for_ikke_samtidig():
    """Rækkefølgen er hele skellet mellem de to mekanismer.

    `wait_for` skal have første forsøg, fordi den giver en ren returkode og
    lader `finally` køre. Bagstopperen dræber processen. Fyrede de samtidig,
    ville et almindeligt async-hæng blive et hårdt drab i stedet for en
    ordentlig exit-kode — og `vagt.cancel()` ville tabe kapløbet.
    """
    assert s._BAGSTOP_MARGIN_S > 0


def test_en_ren_opstart_afbryder_bagstopperen(monkeypatch):
    """Ellers ville den fyre midt i et langsomt, men lovligt svar."""
    ramt: list[int] = []
    monkeypatch.setattr(s, "_AFSLUT", ramt.append)
    monkeypatch.setattr(s, "_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(s, "_BAGSTOP_MARGIN_S", 0.05)

    async def _ok():
        return None

    monkeypatch.setattr(s, "_run_lifespan", _ok)
    assert s.main() == 0

    time.sleep(0.25)
    assert ramt == [], "bagstopperen fyrede efter en ren opstart"


def test_testclient_bruges_IKKE_som_kontekst():
    """`with TestClient(app)` kører app'ens lifespan ÉN GANG TIL.

    Røgprøven står allerede inde i `app.router.lifespan_context(app)`, så
    kontekst-formen starter hver daemon to gange. Målt 25/9-2026 stod
    `recurring-tasks-poller` og `prompt-cache-prewarm` dobbelt blandt de 28
    tråde der var i live ved exit — og flere tråde er flere chancer for at
    fortolkerens nedlukning rammer én midt i et C++-kald.

    AST frem for `in src`: strengen «TestClient» står også i importlinjen og i
    denne kommentar, så et navnetjek ville måle sig selv.
    """
    import ast
    import pathlib

    traeet = ast.parse(
        pathlib.Path("scripts/smoke_test_startup.py").read_text(encoding="utf-8"))

    for n in ast.walk(traeet):
        if not isinstance(n, (ast.With, ast.AsyncWith)):
            continue
        for punkt in n.items:
            kaldt = punkt.context_expr
            if not isinstance(kaldt, ast.Call):
                continue
            navn = getattr(kaldt.func, "id", "") or getattr(kaldt.func, "attr", "")
            assert navn != "TestClient", (
                f"linje {n.lineno}: TestClient som kontekst koerer lifespan "
                "en gang til — brug `TestClient(app)` uden `with`"
            )
