"""Forbindelsen til den maskine sessionen koerer paa — tre tilstande, ikke to."""
from apps.api.jarvis_api.routes import chat as r


def _bro(svar, *, bro_findes=True, monkeypatch=None):
    """Erstat bro-kaldet, og GEM den kommando der blev sendt.

    Uden at gemme kommandoen maaler testen kun parsningen: fjerner man
    `hostname` fra kaldet, staar svaret der stadig fordi det er mocket, og
    testen bliver groen paa noget der er brudt. (Det skete - mutationen var
    groen foerste gang.)
    """
    kaldt: dict[str, str] = {}

    def _exec(navn, args):
        kaldt["cmd"] = str(args.get("command") or "")
        return svar

    monkeypatch.setattr(r, "_operator_exec", _exec)
    monkeypatch.setattr(r, "_bro_findes", lambda uid: bro_findes)
    return kaldt


def test_vaertsnavnet_kommer_FRA_maskinen(monkeypatch):
    # Bro-registret kender kun klientens id («jarvisx-electron»), ikke vaerten.
    ud = "main\n@@@\n M a.py\n@@@\n3\t1\ta.py\n@@@\nCheifOne\n"
    kaldt = _bro({"status": "ok", "result": {"stdout": ud}}, monkeypatch=monkeypatch)
    d = r._git_status_sync("workstation", "/x", "u1")
    # Kommandoen skal FAKTISK spoerge om det - og i samme tur som git.
    assert "hostname" in kaldt["cmd"]
    assert kaldt["cmd"].count("@@@") == 3
    assert d["host"] == "CheifOne"
    assert d["link"] == "ok"
    assert d["added"] == 3 and d["removed"] == 1


def test_bro_der_FINDES_men_ikke_svarer_er_GENFORBINDER(monkeypatch):
    # En desk der genstarter staar registreret et oejeblik endnu. At kalde det
    # «nede» ville faa prikken til at blinke roedt hver gang nogen genstartede.
    _bro({"status": "error"}, bro_findes=True, monkeypatch=monkeypatch)
    d = r._git_status_sync("workstation", "/x", "u1")
    assert d["link"] == "genforbinder"


def test_INGEN_bro_er_nede(monkeypatch):
    _bro({"status": "error"}, bro_findes=False, monkeypatch=monkeypatch)
    assert r._git_status_sync("workstation", "/x", "u1")["link"] == "nede"


def test_tomt_svar_med_levende_bro_er_ogsaa_genforbinder(monkeypatch):
    # status=ok men intet output: kommandoen naaede ikke igennem.
    _bro({"status": "ok", "result": {"stdout": ""}}, bro_findes=True, monkeypatch=monkeypatch)
    assert r._git_status_sync("workstation", "/x", "u1")["link"] == "genforbinder"


def test_uden_hostname_segment_staar_vaerten_tom_frem_for_at_gaette(monkeypatch):
    # En aeldre bro-klient kan svare uden det fjerde segment.
    ud = "main\n@@@\n@@@\n"
    _bro({"status": "ok", "result": {"stdout": ud}}, monkeypatch=monkeypatch)
    d = r._git_status_sync("workstation", "/x", "u1")
    assert d["link"] == "ok"
    assert "host" not in d or d["host"] == ""
