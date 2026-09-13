"""OpenRouter billed-generering — generering, redigering og de tavse svigt.

To ting blev målt 13/9-2026 og låst fast her:

1. **Eventet fyredes aldrig.** `event_bus.publish({...})` (dict-form) raiser
   inde i `Event.create` — `'dict' object has no attribute 'partition'` — og
   kaldstedets `except` slugte det. Målt: 26 kaldsteder i kodebasen brugte
   formen, og `pollinations.*` + `openrouter_image.*` havde 0 events
   nogensinde. Testen kræver at første argument er en STRENG i en tilladt
   familie; på den gamle kode fanger den et dict.

2. **`register_generated_image` fejlede lydløst** til `attachment_id = ""`.
   Billedet lå på disken, men var usynligt i samtalen — og brugeren fik et
   svar uden billede uden at nogen kunne se hvorfor.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import pytest

from core.tools import openrouter_image_tools as t

# 1x1 PNG — rigtige bytes, så dekodning og media_type-udledning testes ægte.
_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA"
    "60e6kgAAAABJRU5ErkJggg=="
)


def _svar(b64: str = _PNG_B64, media: str = "image/png", cost: float = 0.0) -> dict:
    return {
        "data": [{"b64_json": b64, "media_type": media}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "cost": cost},
    }


@pytest.fixture(autouse=True)
def _ingen_cost_bogfoering(monkeypatch):
    """Tests må ikke skrive i produktionens cost-ledger."""
    monkeypatch.setattr(t, "_report_cost", lambda usage, *, model, run_id="": 0.0)


# ── 1. Eventet: formen der gør det levende ───────────────────────────────────


def test_event_kind_er_en_tilladt_familie():
    """Koblingen skal virke HELE vejen: familie tilladt + kind accepteret."""
    from core.eventbus.events import ALLOWED_EVENT_FAMILIES, Event

    family = t._EVENT_KIND.split(".", 1)[0]
    assert family in ALLOWED_EVENT_FAMILIES, (
        f"familien {family!r} er ikke i ALLOWED_EVENT_FAMILIES — publish raiser "
        "og fejlen sluges, så eventet fyrer aldrig"
    )
    Event.create(kind=t._EVENT_KIND, payload={})  # må ikke raise


def test_dict_formen_raiser_og_bliver_slugt():
    """Præmissen for hele fundet. Holder den ikke, beskytter testene intet."""
    from core.eventbus.events import Event

    with pytest.raises(AttributeError):
        Event.create(kind={"kind": "tool.x", "payload": {}})  # type: ignore[arg-type]


def test_eventet_udsendes_med_kind_som_streng(tmp_path, monkeypatch):
    """REGRESSION 13/9-2026: på den gamle kode blev `publish` kaldt med et dict
    som første argument. Her fanges kaldet, og et dict ville fejle assertion'en."""
    fanget: dict = {}

    class _FakeBus:
        def publish(self, kind, payload=None, **kw):  # noqa: ANN001
            fanget["kind"] = kind
            fanget["payload"] = payload

    import core.eventbus.bus as bus_mod

    monkeypatch.setattr(bus_mod, "event_bus", _FakeBus())

    res = t._save_images(
        _svar(), prompt="ravn", model="m", gen_id="orimg-abc123", save_dir=tmp_path
    )
    assert res["status"] == "ok"
    assert isinstance(fanget["kind"], str), "kind skal være en streng, ikke et dict"
    assert fanget["kind"] == t._EVENT_KIND
    assert fanget["payload"]["generation_id"] == "orimg-abc123"
    assert fanget["payload"]["count"] == 1


# ── 2. Gemning, sidecar og attachment ────────────────────────────────────────


def test_save_skriver_fil_og_sidecar(tmp_path):
    res = t._save_images(
        _svar(), prompt="test ravn", model="google/gemini-2.5-flash-image",
        gen_id="orimg-abc123", save_dir=tmp_path,
    )
    assert res["status"] == "ok"
    p = Path(res["path"])
    assert p.is_file()
    assert p.read_bytes() == base64.b64decode(_PNG_B64)
    meta = json.loads(p.with_suffix(p.suffix + ".json").read_text(encoding="utf-8"))
    assert meta["generation_id"] == "orimg-abc123"
    assert meta["prompt"] == "test ravn"
    assert meta["model"] == "google/gemini-2.5-flash-image"


def test_udvidelsen_kommer_fra_media_type(tmp_path):
    """Målt 13/9-2026: bad man om png, svarede modellen image/jpeg. Udvidelsen
    skal følge svaret — ikke ønsket."""
    res = t._save_images(
        _svar(media="image/jpeg"), prompt="p", model="m", gen_id="g", save_dir=tmp_path
    )
    assert res["path"].endswith(".jpg")


def test_intet_billede_i_svaret_giver_fejl(tmp_path):
    res = t._save_images(
        {"data": [], "usage": {}}, prompt="p", model="m", gen_id="g", save_dir=tmp_path
    )
    assert res["status"] == "error"


def test_attachment_registreres(tmp_path, monkeypatch):
    kaldt: list[tuple[str, str]] = []

    def _fake(*, local_path, mime_type="image/jpeg", source_url="", session_id=None):
        kaldt.append((local_path, mime_type))
        return "att_1"

    import core.services.attachment_service as att

    monkeypatch.setattr(att, "register_generated_image", _fake)

    res = t._save_images(
        _svar(), prompt="p", model="m", gen_id="g", save_dir=tmp_path
    )
    assert res["attachment_id"] == "att_1"
    assert kaldt and kaldt[0][1] == "image/png"


def test_attachment_fejl_logges_og_billedet_bevares(tmp_path, monkeypatch, caplog):
    """Fejler registreringen, er billedet usynligt — men det skal SIGES."""
    def _boom(**kw):  # noqa: ANN003
        raise RuntimeError("db nede")

    import core.services.attachment_service as att

    monkeypatch.setattr(att, "register_generated_image", _boom)

    with caplog.at_level(logging.WARNING):
        res = t._save_images(
            _svar(), prompt="p", model="m", gen_id="g", save_dir=tmp_path
        )
    assert res["status"] == "ok"       # billedet findes på disken
    assert res["attachment_id"] == ""  # men er ikke synligt i samtalen
    assert any("kunne ikke registrere" in r.message for r in caplog.records)


# ── 3. Referencer (billed-redigering) ────────────────────────────────────────


def test_reference_fra_sti_bliver_dataurl(tmp_path):
    f = tmp_path / "a.png"
    f.write_bytes(base64.b64decode(_PNG_B64))
    ref = t._as_reference(str(f))
    assert ref is not None
    assert ref["image_url"]["url"].startswith("data:image/png;base64,")


def test_reference_url_sendes_uændret():
    ref = t._as_reference("https://example.test/x.png")
    assert ref is not None
    assert ref["image_url"]["url"] == "https://example.test/x.png"


def test_ulæselig_reference_giver_none(tmp_path):
    assert t._as_reference(str(tmp_path / "findes-ikke.png")) is None
    assert t._as_reference("") is None


# ── 4. Nøglevalg ─────────────────────────────────────────────────────────────


def test_free_tier_profilen_afvises(monkeypatch):
    """`account2` er free-tier-nøglen. Direkte brug fra vores IP er et ToS-brud
    Bjørn eksplicit har forbudt — den skal afvises tydeligt, ikke give 402."""
    import core.runtime.secrets as sec

    monkeypatch.setattr(
        sec, "read_runtime_key",
        lambda key, **kw: "account2" if key == "openrouter_image_profile" else "",
    )
    with pytest.raises(RuntimeError, match="free-tier"):
        t._credentials()


# ── 5. Kaldets form ──────────────────────────────────────────────────────────


def test_generering_sender_input_references(tmp_path, monkeypatch):
    fanget: dict = {}

    def _fake_post(body, *, timeout=0):  # noqa: ANN001
        fanget["body"] = body
        return {"status": "ok", "data": {"data": [], "usage": {}}}

    monkeypatch.setattr(t, "_post", _fake_post)
    monkeypatch.setattr(t, "_save_images", lambda *a, **k: {"status": "ok"})

    f = tmp_path / "in.png"
    f.write_bytes(base64.b64decode(_PNG_B64))
    res = t.generate_image(prompt="gør den blå", references=[str(f)], model="m")

    assert res["status"] == "ok"
    refs = fanget["body"]["input_references"]
    assert len(refs) == 1
    assert refs[0]["image_url"]["url"].startswith("data:image/png")
    assert fanget["body"]["prompt"] == "gør den blå"


def test_ulæselig_reference_stopper_kaldet(monkeypatch):
    """En reference der ikke kan læses skal fejle ÆRLIGT — ikke sende et tomt
    billede afsted og lade modellen gætte."""
    kaldt: list[int] = []

    def _fake_post(body, *, timeout=0):  # noqa: ANN001
        kaldt.append(1)
        return {"status": "ok", "data": {}}

    monkeypatch.setattr(t, "_post", _fake_post)
    res = t.generate_image(prompt="x", references=["/findes/slet/ikke.png"])
    assert res["status"] == "error"
    assert not kaldt, "kaldet må ikke sendes med en ulæselig reference"


def test_tom_prompt_afvises():
    assert t.generate_image(prompt="   ")["status"] == "error"


# ── 6. Executors ─────────────────────────────────────────────────────────────


def test_exec_generer_kræver_prompt():
    assert t._exec_openrouter_image({})["status"] == "error"


def test_exec_rediger_kræver_både_reference_og_prompt():
    assert t._exec_openrouter_image_edit({"prompt": "x"})["status"] == "error"
    assert t._exec_openrouter_image_edit({"reference": "a.png"})["status"] == "error"


def test_exec_rediger_accepterer_alternative_reference_navne(monkeypatch):
    """`image_path` og `image_url` er accepterede aliaser for `reference`."""
    fanget: dict = {}
    monkeypatch.setattr(
        t, "edit_image",
        lambda **kw: fanget.update(kw) or {"status": "ok", "bytes": 1,
                                           "media_type": "image/png",
                                           "cost_usd": 0.0, "path": "/x"},
    )
    res = t._exec_openrouter_image_edit({"image_path": "/a.png", "prompt": "rød"})
    assert res["status"] == "ok"
    assert fanget["reference"] == "/a.png"


# ── 7. Værktøjs-definitioner ─────────────────────────────────────────────────


def test_definitionerne_har_de_påkrævede_felter():
    navne = {d["function"]["name"]: d for d in t.OPENROUTER_IMAGE_TOOL_DEFINITIONS}
    assert set(navne) == {"openrouter_image", "openrouter_image_edit"}
    assert navne["openrouter_image"]["function"]["parameters"]["required"] == ["prompt"]
    assert set(
        navne["openrouter_image_edit"]["function"]["parameters"]["required"]
    ) == {"reference", "prompt"}


def test_definitionerne_nævner_prisen():
    """Værktøjet er BETALT — det skal stå i beskrivelsen, ikke skjules."""
    for d in t.OPENROUTER_IMAGE_TOOL_DEFINITIONS:
        assert "PAID" in d["function"]["description"]
