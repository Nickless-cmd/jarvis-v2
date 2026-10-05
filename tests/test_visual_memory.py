"""Tests for core.services.visual_memory — coarse age bucketing."""

import base64 as _b64

import numpy as _np
import pytest

from core.services import visual_memory as VM
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


def test_hjaelperen_uden_force_config_bruger_den_valgte_synsmodel(monkeypatch):
    """Uden force_config gælder det valgte syn — det er vejen for BILLEDER.

    Bjørn 5/9-2026: «med syn bruger tools flash model med syn.» Den beslutning
    står ved magt for læsning af billeder han selv sender
    (`attachment_service`). SANSKNINGS-vejen er undtagelsen (5/10-2026): den
    tvinger config-modellen, fordi en tænke-model skriver sin egen instruktion
    ind i indtrykket. Se
    `test_sansnings_vejen_kigger_gennem_config_modellen`.
    """
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


def test_archive_sensory_siger_falsk_for_kvittering(isolated_runtime) -> None:
    """«Intet mærkbart ændret.» er et gyldigt udfald af at kigge — ikke et indtryk.

    Den passive kadence arkiverede hvert svar uanset indhold. Målt 28/9-2026:
    45 sådanne poster. Tick'en skal kunne sige «unchanged» i stedet for at
    bogføre en sansning der aldrig blev skrevet.
    """
    assert VM._archive_sensory("Intet mærkbart ændret.", metadata={}) is False
    assert VM._archive_sensory(
        "En kop damper stadig på bordet, lyset er skiftet mod vest.", metadata={}
    ) is True


# ---------------------------------------------------------------------------
# Dødt frame: vision-vejen må ikke DIGTE et rum ud af en sort flade (5/10-2026)
#
# Målt samme dag: tre poster i Sansernes Arkiv var ikke sanseindtryk. Modellen
# havde fået et dødt frame og skrev i stedet et digt om mørket, eller svarede
# som en chatbot: «Hvis du uploader billedet igen, vil jeg meget gerne
# beskrive stemningen ...». Værn i ARKIVET ville være formulerings-jagt;
# generatoren er at det døde frame overhovedet når modellen.
# ---------------------------------------------------------------------------


def _jpg(arr) -> str:
    import cv2

    ok, buf = cv2.imencode(".jpg", arr, [cv2.IMWRITE_JPEG_QUALITY, 75])
    assert ok, "kunne ikke kode testbilledet"
    return _b64.b64encode(buf.tobytes()).decode("ascii")


def _doedt_frame() -> str:
    """En død flade: ingen struktur overhovedet."""
    return _jpg(_np.zeros((240, 320, 3), _np.uint8))


def _moerkt_men_levende_frame() -> str:
    """Et MØRKT rum er ikke et dødt frame — ét lysglimt er nok struktur."""
    arr = _np.zeros((240, 320, 3), _np.uint8) + 2
    arr[100:140, 150:170] = 40
    return _jpg(arr)


def _lyst_frame() -> str:
    return _jpg((_np.random.rand(240, 320, 3) * 200 + 55).astype(_np.uint8))


def test_doedt_frame_har_ingen_struktur():
    ud = VM._billede_er_doedt(_doedt_frame())
    assert ud["doedt"] is True
    assert ud["std"] is not None and ud["std"] < VM._MINDSTE_STRUKTUR


def test_moerkt_rum_er_IKKE_et_doedt_frame():
    """Falsk-positiv-vagten — den vigtigste af dem alle.

    Et mørkt rum er en ægte sansning: målt 17/9-2026 beskrev arkivet «kun en
    svag kornet tekstur anes», og 25/9 «rummet er lukket og sovende». Havde
    gaten spist dem, ville den have dræbt nattens eneste rigtige indtryk for
    at undgå tre digte.
    """
    ud = VM._billede_er_doedt(_moerkt_men_levende_frame())
    assert ud["doedt"] is False, ud["grund"]


def test_lyst_frame_er_brugbart():
    assert VM._billede_er_doedt(_lyst_frame())["doedt"] is False


def test_uaflaeseligt_frame_regnes_som_doedt():
    """Hvad vi ikke kan måle, kan modellen heller ikke se."""
    ud = VM._billede_er_doedt("ikke-base64-overhovedet")
    assert ud["doedt"] is True
    assert ud["std"] is None


def _stub_kaeden(monkeypatch, b64: str) -> list[str]:
    """Stub hele vejen frem til arkivet. Returnerer de arkiverede tekster."""
    arkiveret: list[str] = []
    monkeypatch.setattr(VM, "_enabled", lambda: True)
    monkeypatch.setattr(VM, "_vision_model", lambda **_k: ("test-model", "ollama"))
    monkeypatch.setattr(VM, "_prune_old_records", lambda: None)
    monkeypatch.setattr(VM, "_load_records", lambda: [])
    monkeypatch.setattr(VM, "set_runtime_state_value", lambda *_a, **_k: None)
    monkeypatch.setattr(VM, "_capture_image", lambda *_a, **_k: (b64, "testkamera"))
    monkeypatch.setattr(VM, "_describe_image", lambda *_a, **_k: "Rummet føles stille.")
    monkeypatch.setattr(
        VM, "_archive_sensory", lambda d, **_k: (arkiveret.append(d) or True)
    )
    return arkiveret


def test_look_around_digter_IKKE_paa_et_doedt_frame(monkeypatch):
    arkiveret = _stub_kaeden(monkeypatch, _doedt_frame())
    ud = VM.look_around_now()
    assert ud["status"] == "image_unusable", ud
    assert arkiveret == [], "et dødt frame blev arkiveret som et indtryk"


def test_kadencen_digter_IKKE_paa_et_doedt_frame(monkeypatch):
    arkiveret = _stub_kaeden(monkeypatch, _doedt_frame())
    ud = VM.tick_visual_memory_daemon()
    assert ud["status"] == "image_unusable", ud
    assert arkiveret == [], "kadencen arkiverede et indtryk fra en død flade"


def test_levende_frame_gaar_uaendret_igennem(monkeypatch):
    """Regression: gaten må ikke blokere den normale sansning."""
    arkiveret = _stub_kaeden(monkeypatch, _moerkt_men_levende_frame())
    ud = VM.look_around_now()
    assert ud["status"] == "captured", ud
    assert arkiveret == ["Rummet føles stille."]


# ---------------------------------------------------------------------------
# Sansnings-vejen tvinger CONFIG-modellen (5/10-2026)
#
# `force_config` blev bygget til netop dette og var kaldt af ingen: hele
# sansnings-vejen gik gennem `_vision_model()` uden argument og lånte dermed
# øjnene fra den tur der kørte lige nu. Er den en tænke-model, skriver den sin
# egen instruktion ind i «indtrykket» — målt 2/10-2026 var dagens eneste
# visuelle sans 100% prompt-lækage. Værnene i arkivet fanger formuleringer;
# generatoren er at vejen overhovedet spørger den model.
# ---------------------------------------------------------------------------


def _stub_sansning(monkeypatch, *, b64: str) -> list[tuple[object, object]]:
    """Stub hele kæden og fang (model, provider) der blev spurgt."""
    from core.services import vision_backend as VB

    brugt: list[tuple[object, object]] = []
    monkeypatch.setattr(
        VB, "active_visible_target", lambda: ("deepseek", "deepseek-flash")
    )
    monkeypatch.setattr(
        VM, "load_settings",
        lambda: _Settings({"vision_model_name": "gemma4:31b-cloud"}),
    )
    monkeypatch.setattr(VM, "_enabled", lambda: True)
    monkeypatch.setattr(VM, "_prune_old_records", lambda: None)
    monkeypatch.setattr(VM, "_load_records", lambda: [])
    monkeypatch.setattr(VM, "set_runtime_state_value", lambda *_a, **_k: None)
    monkeypatch.setattr(VM, "_archive_sensory", lambda d, **_k: True)
    monkeypatch.setattr(VM, "_capture_image", lambda *_a, **_k: (b64, "testkamera"))
    monkeypatch.setattr(
        VM, "_describe_image",
        lambda *_a, **k: (
            brugt.append((k.get("model"), k.get("provider")))
            or "Rummet føles stille."
        ),
    )
    return brugt


def test_sansnings_vejen_kigger_gennem_config_modellen(monkeypatch):
    """Den valgte tur-model må ikke låne sine øjne til en sansning."""
    brugt = _stub_sansning(monkeypatch, b64=_lyst_frame())

    VM.look_around_now()
    VM.tick_visual_memory_daemon()

    assert brugt == [("gemma4:31b-cloud", "ollama")] * 2, brugt


def test_fladen_siger_config_modellen_ikke_tur_modellen(monkeypatch):
    """Feltet heder `configured_model` — og efter 5/10-2026 er det sandt."""
    _stub_sansning(monkeypatch, b64=_lyst_frame())
    assert VM.build_visual_memory_surface()["configured_model"] == "gemma4:31b-cloud"
