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
