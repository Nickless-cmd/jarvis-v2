"""Tests for core.services.visual_memory — coarse age bucketing."""

from core.services.visual_memory import _coarse_age_label


def test_lige_nu():
    assert _coarse_age_label(0) == "(lige nu)"
    assert _coarse_age_label(4) == "(lige nu)"


def test_få_min():
    assert _coarse_age_label(5) == "(for få min siden)"
    assert _coarse_age_label(14) == "(for få min siden)"


def test_sidste_time():
    assert _coarse_age_label(15) == "(inden for sidste time)"
    assert _coarse_age_label(59) == "(inden for sidste time)"


def test_par_timer():
    assert _coarse_age_label(60) == "(for et par timer siden)"
    assert _coarse_age_label(179) == "(for et par timer siden)"


def test_tidligere_i_dag():
    assert _coarse_age_label(180) == "(tidligere i dag)"
    assert _coarse_age_label(719) == "(tidligere i dag)"


def test_et_stykke_tid():
    assert _coarse_age_label(720) == "(for et stykke tid siden)"
    assert _coarse_age_label(1439) == "(for et stykke tid siden)"


def test_dage():
    assert _coarse_age_label(1440) == "(for 1 dag siden)"
    assert _coarse_age_label(2880) == "(for 2 dage siden)"


def test_over_en_uge():
    assert _coarse_age_label(7 * 1440) == "(for over en uge siden)"


def test_cache_stability_window():
    """Within a single bucket, the label must NOT change. Critical for
    prompt-cache prefix stability — see commit message."""
    # 3-12h bucket: every value should produce same label
    labels = {_coarse_age_label(m) for m in range(180, 720, 30)}
    assert labels == {"(tidligere i dag)"}
    # 12-24h bucket
    labels = {_coarse_age_label(m) for m in range(720, 1440, 60)}
    assert labels == {"(for et stykke tid siden)"}


# ---------------------------------------------------------------------------
# Kameraregistret: rammer det rigtige kamera — og siger til når det ikke kan
# ---------------------------------------------------------------------------

import pytest

from core.services import visual_memory as VM


class _Settings:
    def __init__(self, extra: dict) -> None:
        self.extra = extra


def _tom_config(monkeypatch):
    """Uden config skal det indbyggede kamerakort gælde."""
    monkeypatch.setattr(VM, "load_settings", lambda: _Settings({}))


def test_kameranavne_taaler_dansk_og_store_bogstaver(monkeypatch):
    _tom_config(monkeypatch)
    for skrivemaade in ("stue", "Stuen", "STUE", "aqara", "living room"):
        assert VM.resolve_camera(skrivemaade)[0] == "stue", skrivemaade


def test_oe_folder_sammen_med_o(monkeypatch):
    _tom_config(monkeypatch)
    assert VM.resolve_camera("hoveddør")[0] == "hoveddor"
    assert VM.resolve_camera("hoveddoren")[0] == "hoveddor"
    assert VM.resolve_camera("udendørs")[0] == "hoveddor"
    assert VM.resolve_camera("dørklokken")[0] == "dorklokke"


def test_entity_id_kan_bruges_direkte(monkeypatch):
    _tom_config(monkeypatch)
    key, cam = VM.resolve_camera("camera.x7_smart_doorbell")
    assert key == "dorklokke"
    assert cam["entity"] == "camera.x7_smart_doorbell"


def test_tomt_navn_giver_standardkameraet(monkeypatch):
    _tom_config(monkeypatch)
    assert VM.resolve_camera("")[0] == "stue"


def test_ukendt_kamera_naevner_de_gyldige(monkeypatch):
    _tom_config(monkeypatch)
    with pytest.raises(ValueError) as fejl:
        VM.resolve_camera("kælderen")
    besked = str(fejl.value)
    assert "kælderen" in besked
    assert "hoveddor" in besked and "stue" in besked


def test_gammel_enkeltkamera_config_peger_stadig_rigtigt(monkeypatch):
    """Opgraderingen må ikke tabe det kamera den tidligere config pegede på."""
    monkeypatch.setattr(
        VM, "load_settings",
        lambda: _Settings({"visual_memory_ha_camera_entity": "camera.kamera_over_hoveddor"}),
    )
    assert VM.default_camera() == "hoveddor"


def test_config_kan_overskrive_kamerakortet(monkeypatch):
    monkeypatch.setattr(
        VM, "load_settings",
        lambda: _Settings({"visual_memory_cameras": {
            "garage": {"kind": "ha", "entity": "camera.garage", "label": "garagen"},
        }}),
    )
    assert VM.resolve_camera("garage")[0] == "garage"
    assert VM.default_camera() == "garage"


def test_valgt_kamera_ender_som_det_rigtige_entity_id(monkeypatch):
    _tom_config(monkeypatch)
    kaldt: list[str] = []
    monkeypatch.setattr(
        VM, "_capture_ha_camera",
        lambda entity_id="": (kaldt.append(entity_id) or "BILLEDE"),
    )
    b64, key, label = VM.capture_from_camera("dørklokken")
    assert (b64, key) == ("BILLEDE", "dorklokke")
    assert kaldt == ["camera.x7_smart_doorbell"]
    assert "dørklokken" in label


def test_webcam_gaar_uden_om_home_assistant(monkeypatch):
    _tom_config(monkeypatch)
    monkeypatch.setattr(VM, "_capture_webcam", lambda: "LOKALT")
    monkeypatch.setattr(
        VM, "_capture_ha_camera",
        lambda entity_id="": pytest.fail("webcam må ikke gå gennem Home Assistant"),
    )
    assert VM.capture_from_camera("webcam")[0] == "LOKALT"


def test_navngivet_kamera_fejler_hoejlydt(monkeypatch):
    """Spørger man om hoveddøren, må man ikke tavst få stuen at se."""
    _tom_config(monkeypatch)
    monkeypatch.setattr(
        VM, "_capture_ha_camera",
        lambda entity_id="": (_ for _ in ()).throw(RuntimeError("HTTP 500")),
    )
    monkeypatch.setattr(VM, "_capture_webcam", lambda: "FALDT TILBAGE")
    with pytest.raises(RuntimeError):
        VM._capture_image("hoveddor")


def test_look_around_bruger_den_valgte_synsmodel(monkeypatch):
    """Har Bjørn valgt syns-modellen, skal look_around kigge gennem den."""
    from core.services import vision_backend as VB

    monkeypatch.setattr(
        VB, "active_visible_target",
        lambda: ("deepseek", "deepseek-v4-flash-vision-exp"),
    )
    assert VM._vision_model() == ("deepseek-v4-flash-vision-exp", "deepseek")


def test_uden_aktivt_valg_gaelder_config(monkeypatch):
    """Daemon-stien kører uden tur — så er runtime-config stadig sandheden."""
    from core.services import vision_backend as VB

    monkeypatch.setattr(VB, "active_visible_target", lambda: ("", ""))
    monkeypatch.setattr(
        VM, "load_settings",
        lambda: _Settings({"vision_model_name": "gemma4:31b-cloud"}),
    )
    assert VM._vision_model() == ("gemma4:31b-cloud", "ollama")


def test_deepseek_billede_gaar_ikke_til_ollama(monkeypatch):
    from core.services import vision_backend as VB

    monkeypatch.setattr(
        VM, "_describe_via_ollama",
        lambda *a, **k: pytest.fail("DeepSeek-billede må ikke gå til Ollama"),
    )
    monkeypatch.setattr(VB, "describe_via_deepseek",
                        lambda b64, *, model, prompt, run_id="": "set i stuen")
    ud = VM._describe_image("B64", model="deepseek-v4-flash-vision-exp",
                            provider="deepseek", prompt="hvad ser du?")
    assert ud == "set i stuen"


def test_ascii_stavning_rammer_samme_kamera(monkeypatch):
    """Jarvis skriver dansk paa begge maader — begge skal ramme."""
    _tom_config(monkeypatch)
    for skrivemaade in ("hoveddør", "hoveddoer", "hoveddoeren", "hoveddor"):
        assert VM.resolve_camera(skrivemaade)[0] == "hoveddor", skrivemaade
    for skrivemaade in ("dørklokke", "doerklokke", "doerklokken"):
        assert VM.resolve_camera(skrivemaade)[0] == "dorklokke", skrivemaade
