"""Billeder pr. samtale — baade dem Jarvis lavede og dem brugeren sendte."""
from pathlib import Path

from core.services.attachment_service import (
    GENERERET, list_image_attachments, register_generated_image,
)


def _billede(tmp_path: Path, navn: str = "b.jpg") -> str:
    p = tmp_path / navn
    p.write_bytes(b"\xff\xd8\xff" + b"0" * 40)   # nok til at have en stoerrelse
    return str(p)


def test_et_genereret_billede_bliver_synligt(isolated_runtime, tmp_path):
    # FØR: filen laa i workspace'et og INGEN klient kunne se den.
    aid = register_generated_image(local_path=_billede(tmp_path), session_id="s1")
    assert aid
    raekker = list_image_attachments(session_id="s1")
    assert [r["attachment_id"] for r in raekker] == [aid]


def test_ophavet_kommer_med_ud(isolated_runtime, tmp_path):
    # Uden channel_type ville galleriet vaere en bunke uden ophav.
    register_generated_image(local_path=_billede(tmp_path), session_id="s1")
    assert list_image_attachments(session_id="s1")[0]["channel_type"] == GENERERET


def test_UDEN_session_registreres_der_ikke(isolated_runtime, tmp_path):
    # Et billede uden ophav ville dukke op i ENHVER samtales liste.
    assert register_generated_image(local_path=_billede(tmp_path), session_id="") == ""
    assert list_image_attachments() == []


def test_en_fil_der_ikke_findes_registreres_ikke(isolated_runtime, tmp_path):
    assert register_generated_image(local_path=str(tmp_path / "findes-ikke.jpg"),
                                    session_id="s1") == ""


def test_session_filteret_skiller_samtalerne(isolated_runtime, tmp_path):
    a = register_generated_image(local_path=_billede(tmp_path, "a.jpg"), session_id="s1")
    b = register_generated_image(local_path=_billede(tmp_path, "b.jpg"), session_id="s2")
    assert [r["attachment_id"] for r in list_image_attachments(session_id="s1")] == [a]
    assert [r["attachment_id"] for r in list_image_attachments(session_id="s2")] == [b]


def test_UDELADT_session_giver_ALT(isolated_runtime, tmp_path):
    # Desk's galleri kalder uden og skal blive ved med at faa hele historikken.
    register_generated_image(local_path=_billede(tmp_path, "a.jpg"), session_id="s1")
    register_generated_image(local_path=_billede(tmp_path, "b.jpg"), session_id="s2")
    assert len(list_image_attachments()) == 2


def test_vaerktoejet_KALDER_registreringen():
    # Mekanismen findes-kalderen-mangler er husets hyppigste fejl.
    import inspect
    from core.tools import pollinations_tools
    kilde = inspect.getsource(pollinations_tools)
    assert "register_generated_image(" in kilde
    assert '"attachment_id": attachment_id' in kilde


# ---------------------------------------------------------------------------
# Kanal-afsendelse — billedet skal NÅ frem, ikke bare registreres (27/9-2026)
#
# Målt: Bjørn bad om et billede på Discord. Det blev genereret (1.240.612
# bytes) og registreret — og var usynligt. Desk viser billedet fordi
# SSE-streamen bærer en image-blok; Discord har ingen blok-rendering og skal
# have filen. Koblingen fandtes ikke, og validate_send_path afviste end ikke
# stien manuelt.
# ---------------------------------------------------------------------------


def test_genereret_billede_sendes_til_kanalen(monkeypatch, isolated_runtime, tmp_path):
    import core.services.discord_gateway as gw

    sendt: list[dict] = []
    monkeypatch.setattr(gw, "get_discord_channel_for_session", lambda sid: 4242)
    monkeypatch.setattr(gw, "send_discord_file", lambda **kw: sendt.append(kw))

    sti = _billede(tmp_path)
    aid = register_generated_image(local_path=sti, session_id="discord-s1")

    assert aid
    assert sendt == [{"channel_id": 4242, "text": "", "file_path": sti}]


def test_uden_kanal_sendes_intet(monkeypatch, isolated_runtime, tmp_path):
    # En desk-samtale har ingen Discord-kanal — så må intet sendes.
    import core.services.discord_gateway as gw

    sendt: list[dict] = []
    monkeypatch.setattr(gw, "get_discord_channel_for_session", lambda sid: None)
    monkeypatch.setattr(gw, "send_discord_file", lambda **kw: sendt.append(kw))

    register_generated_image(local_path=_billede(tmp_path), session_id="web-s1")

    assert sendt == []


def test_fejlende_afsendelse_koster_ikke_registreringen(
    monkeypatch, isolated_runtime, tmp_path
):
    # Kanalen må ikke kunne vælte en generering der lykkedes. Afsendelsen
    # ligger derfor UDEN FOR registreringens try — rækken er allerede skrevet.
    import core.services.discord_gateway as gw

    def _kanal_nede(**kw):
        raise RuntimeError("discord nede")

    monkeypatch.setattr(gw, "get_discord_channel_for_session", lambda sid: 4242)
    monkeypatch.setattr(gw, "send_discord_file", _kanal_nede)

    aid = register_generated_image(local_path=_billede(tmp_path), session_id="s1")

    assert aid
    assert [r["attachment_id"] for r in list_image_attachments(session_id="s1")] == [aid]


def test_genereret_mappe_er_en_tilladt_afsender_rod():
    # Rødderne var kun uploads/ og workspaces/ — billeder ligger i
    # shared/memory/generated/. Uden roden kunne intet genereret billede sendes.
    import core.services.attachment_service as svc
    from core.tools.openrouter_image_tools import _generated_dir

    genereret = _generated_dir().resolve()
    assert any(
        genereret.is_relative_to(rod.resolve()) for rod in svc._allowed_send_roots()
    ), f"{genereret} er ikke under nogen tilladt afsender-rod"


def test_en_nabomappe_til_roden_afvises(tmp_path, monkeypatch):
    # Prefix-sammenligning lukkede `<rod>-evil/` ind som om den laa UNDER
    # roden. is_relative_to goer den ikke — det er en sikkerhedsgroense.
    import core.services.attachment_service as svc

    rod = tmp_path / "uploads"
    rod.mkdir()
    nabo = tmp_path / "uploads-evil"
    nabo.mkdir()
    f = nabo / "fil.jpg"
    f.write_bytes(b"data")

    monkeypatch.setattr(svc, "_ALLOWED_SEND_ROOTS", [rod])
    ok, fejl = svc.validate_send_path(str(f))
    assert not ok
    assert "not-allowed" in fejl


def test_et_genereret_billede_passerer_sti_valideringen(tmp_path):
    # Den funktionelle side af roden: en fil i genereret-mappen skal igennem.
    # Målt før fixet: (False, 'not-allowed') — mens en upload gik igennem.
    import core.services.attachment_service as svc
    from core.tools.openrouter_image_tools import _generated_dir

    genereret = _generated_dir()
    genereret.mkdir(parents=True, exist_ok=True)
    f = genereret / "_test-afsender-rod.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 24)
    try:
        ok, fejl = svc.validate_send_path(str(f))
        assert ok, fejl
    finally:
        f.unlink(missing_ok=True)
