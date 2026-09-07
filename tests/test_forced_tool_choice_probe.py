"""Sonden der skal afgøre HVORFOR ~22 % af de tvungne runder giver nul kald.

Den ændrer intet — den noterer. Testene holder fast i at den noterer det
rigtige, og at en fejl i målingen aldrig kan vælte den runde den måler.
"""
from core.services import forced_tool_choice_probe as p


def _kald(**over):
    grund = dict(run_id="r1", provider="deepseek", model="deepseek-v4-flash",
                 round_index=3, finish_reason="stop", tool_calls=0,
                 text_chars=210, reasoning_chars=0, tools_advertised=70,
                 thinking_disabled=True)
    grund.update(over)
    return p.note_forced_round(**grund)


def test_nul_kald_er_ikke_honoreret():
    assert _kald(tool_calls=0)["honoreret"] is False


def test_et_kald_er_honoreret():
    assert _kald(tool_calls=1)["honoreret"] is True


def test_konstanten_goeres_synlig():
    # thinking slås fra på HVER tvungen runde (målt på byggeren). Det er altså
    # en konstant og kan ikke forklare de 22 %. Feltet bliver stående for at
    # gøre konstanten synlig i dataene — og fordi et skift til False ville
    # være et fund i sig selv.
    assert _kald(thinking_disabled=True)["thinking_disabled"] is True
    assert _kald(thinking_disabled=False)["thinking_disabled"] is False


def test_finish_reason_skelner_to_forskellige_fejl():
    # DET er variablen der kan skelne: «stop» med prosa = providerne håndhæver
    # ikke `required`. «length» = modellen løb tør undervejs. Hver sin rettelse.
    assert _kald(finish_reason="stop")["finish_reason"] == "stop"
    assert _kald(finish_reason="length")["finish_reason"] == "length"


def test_annoncerede_vaerktoejer_kommer_med():
    # Nul her ville betyde at tools slet ikke blev sendt — en helt anden fejl
    # end at modellen ignorerer required.
    assert _kald(tools_advertised=0)["tools_advertised"] == 0
    assert _kald(tools_advertised=70)["tools_advertised"] == 70


def test_en_daarlig_eventbus_vaelter_ikke_runden(monkeypatch):
    import core.eventbus.bus as bus

    class Sur:
        def publish(self, *a, **k):
            raise RuntimeError("bussen er nede")

    monkeypatch.setattr(bus, "event_bus", Sur())
    assert _kald()["run_id"] == "r1"      # returnerer stadig, kaster ikke


def test_tomme_vaerdier_giver_ikke_none_i_nyttelasten():
    ud = p.note_forced_round(run_id="", provider="", model="", round_index=0,
                             finish_reason="", tool_calls=0, text_chars=0,
                             reasoning_chars=0, tools_advertised=0,
                             thinking_disabled=False)
    assert all(v is not None for v in ud.values())
