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
