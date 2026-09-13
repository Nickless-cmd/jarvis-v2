"""syslogd kan ikke logge sin egen doed — den ER loggeren.

pfSense' syslogd er doed 5-6 gange om dagen i mindst seks doegn (13/9-2026:
00:11, 01:17, 02:15, 03:12, 09:47). Auto-healen virker hver gang, og incidenten
har derfor kun kunnet sige «den var doed, jeg genstartede den».

`grep -ril syslogd /var/log/*.log` paa pfSense giver INGENTING. Det er ikke en
fejl i logningen; det er logisk uundgaaeligt. Uden spor kan aarsagen ikke findes,
og den har staaet uforklaret siden.

MAALT samme dag: disk 6 %, 1,3 GB hukommelse fri, CPU 98,8 % idle. Ingen af de
saedvanlige mistaenkte — hvilket goer sporet endnu vigtigere.
"""
import core.services.infra_sense as isense


def test_attesten_samles_FOER_genstarten(monkeypatch):
    """Bagefter er beviset vaek: en frisk proces har ingen doedsaarsag."""
    import inspect
    kilde = inspect.getsource(isense)
    i_attest = kilde.index("attest = _syslogd_doedsattest()")
    i_heal = kilde.index("healed = _pfsense_restart_syslogd()")
    assert i_attest < i_heal, "sporet samles efter genstarten — for sent"


def test_attesten_spoerger_om_det_der_OVERLEVER_processen(monkeypatch):
    """Kernens ringbuffer husker et OOM-drab; pid-filen afsloerer et drab
    udefra; newsyslog fyrer hvert minut og signalerer netop syslogd."""
    kaldt: list[str] = []
    monkeypatch.setattr(isense, "read_runtime_key", lambda *a, **k: "nøgle", raising=False)
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key", lambda *a, **k: "nøgle")
    monkeypatch.setattr(isense, "_http_json",
                        lambda *a, **k: (kaldt.append(k.get("body", {}).get("command", "")),
                                         {"data": {"output": "svar"}})[1])
    ud = isense._syslogd_doedsattest()
    samlet = " ".join(kaldt)
    assert "dmesg" in samlet
    assert "syslog.pid" in samlet
    assert "system.log" in samlet
    assert "dmesg" in ud and "pidfil" in ud


def test_uden_noegle_gaar_healen_stadig_igennem(monkeypatch):
    """En diagnose der ikke kan hentes maa aldrig forhindre genstarten."""
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key", lambda *a, **k: None)
    assert isense._syslogd_doedsattest() == ""


def test_en_fejlende_diagnose_kaster_ikke(monkeypatch):
    monkeypatch.setattr(
        "core.runtime.secrets.read_runtime_key", lambda *a, **k: "nøgle")
    def _boom(*a, **k):
        raise RuntimeError("API nede")
    monkeypatch.setattr(isense, "_http_json", _boom)
    assert isense._syslogd_doedsattest() == ""


def test_attesten_haenges_paa_incidenten():
    """Ellers staar sporet kun i hukommelsen paa den proces der fandt det."""
    import inspect
    kilde = inspect.getsource(isense)
    assert "SPOR:" in kilde
