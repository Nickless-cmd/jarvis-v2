"""Modellens egne øjne: billeder fra DENNE tur direkte i prompten.

Det vigtigste er hvad der sker naar modellen IKKE kan se: saa skal
beskederne vaere byte-identiske med foer, ellers har vi flyttet cachen for
en funktion der ikke engang bliver brugt.
"""
import json

import pytest

from core.services.attachment_blocks import (
    image_content_blocks,
    image_ids_on_message,
    user_message_content_json,
)


def _json(*blokke):
    return json.dumps(list(blokke))


def test_billed_id_findes_i_blokkene():
    cj = _json({"type": "image", "attachment_id": "a1", "filename": "skaerm.png"},
               {"type": "file", "attachment_id": "f1", "filename": "noter.zip"})
    assert image_ids_on_message(cj) == ["a1"], "kun billeder, ikke filer"


def test_tomt_og_ugyldigt_giver_ingenting():
    assert image_ids_on_message(None) == []
    assert image_ids_on_message("") == []
    assert image_ids_on_message("ikke json") == []
    assert image_ids_on_message('{"ikke": "liste"}') == []


def test_blokke_bygges_af_data_urls(monkeypatch):
    monkeypatch.setattr("core.services.attachment_service.image_data_url",
                        lambda aid: f"data:image/png;base64,{aid}")
    b = image_content_blocks(_json({"type": "image", "attachment_id": "a1"}))
    assert b == [{"type": "image_url", "image_url": {"url": "data:image/png;base64,a1"}}]


def test_utilgaengeligt_billede_springes_over(monkeypatch):
    """En halv reference er vaerre end ingen."""
    monkeypatch.setattr("core.services.attachment_service.image_data_url",
                        lambda aid: None)
    assert image_content_blocks(_json({"type": "image", "attachment_id": "a1"})) == []


def test_loft_paa_antal_billeder(monkeypatch):
    monkeypatch.setattr("core.services.attachment_service.image_data_url",
                        lambda aid: "data:image/png;base64,x")
    cj = _json(*[{"type": "image", "attachment_id": f"a{i}"} for i in range(12)])
    assert len(image_content_blocks(cj)) == 4


def test_referencen_i_den_GEMTE_besked_baerer_stadig_ingen_data():
    """Adgangskontrollen paa /attachments/image/{id} maa ikke omgaas."""
    cj = user_message_content_json([{"id": "a1", "filename": "s.png",
                                     "mime_type": "image/png"}])
    assert "base64" not in (cj or "")
    assert "a1" in (cj or "")


# ── Selve indsaettelsen i prompten ───────────────────────────────────────

def _messages():
    return [{"role": "system", "content": "S"},
            {"role": "user", "content": "hvad ser du?"}]


def test_blind_model_lader_beskederne_vaere_UROERTE(monkeypatch):
    from core.services.visible_model import _giv_modellen_oejne
    monkeypatch.setattr("core.services.chat_sessions.latest_user_content_json",
                        lambda s: _json({"type": "image", "attachment_id": "a1"}))
    m = _messages()
    foer = json.dumps(m)
    _giv_modellen_oejne(m, session_id="s1", model="deepseek-v4-flash")
    assert json.dumps(m) == foer, "en blind model maa ikke flytte cachen"


def test_seende_model_faar_billedet(monkeypatch):
    from core.services.visible_model import _giv_modellen_oejne
    monkeypatch.setattr("core.services.chat_sessions.latest_user_content_json",
                        lambda s: _json({"type": "image", "attachment_id": "a1"}))
    monkeypatch.setattr("core.services.attachment_service.image_data_url",
                        lambda aid: "data:image/png;base64,AAA")
    m = _messages()
    _giv_modellen_oejne(m, session_id="s1", model="deepseek-v4-flash-vision-exp")
    indhold = m[-1]["content"]
    assert isinstance(indhold, list)
    assert indhold[0] == {"type": "text", "text": "hvad ser du?"}
    assert indhold[1]["type"] == "image_url"
    assert m[0]["content"] == "S", "systembeskeden maa ikke roeres"


def test_ingen_vedhaeftning_lader_beskeden_vaere(monkeypatch):
    from core.services.visible_model import _giv_modellen_oejne
    monkeypatch.setattr("core.services.chat_sessions.latest_user_content_json",
                        lambda s: None)
    m = _messages()
    foer = json.dumps(m)
    _giv_modellen_oejne(m, session_id="s1", model="deepseek-v4-flash-vision-exp")
    assert json.dumps(m) == foer


def test_uden_session_sker_der_ingenting():
    from core.services.visible_model import _giv_modellen_oejne
    m = _messages()
    foer = json.dumps(m)
    _giv_modellen_oejne(m, session_id=None, model="deepseek-v4-flash-vision-exp")
    assert json.dumps(m) == foer
