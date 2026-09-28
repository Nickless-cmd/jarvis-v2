"""En genereret video skal naa traaden — ikke bare disken.

## Hvad der var galt (28/9-2026)

`_exec_pollinations_image` gjorde to ting efter en vellykket generering:
registrerede filen som attachment, og lagde en post paa turen. Uden dem er en
fil Jarvis lavede usynlig — klienten renderer efter blokke, saa en sti i prosa
er ikke leveret.

`_exec_pollinations_video` gjorde INGEN af delene. Den returnerede bare
`result`. En video kostede op til 600 sekunder at lave og kunne aldrig vises.

Testene her maaler at video faar samme behandling som billeder — og at
behandlingen er self-safe: en generering der lykkedes maa ikke gaa tabt fordi
et opslag fejlede. Det er ikke en teoretisk bekymring ved ti minutters arbejde.
"""
from __future__ import annotations

import pytest

from core.tools import pollinations_tools as P


@pytest.fixture
def fanget(monkeypatch):
    """Fang hvad vaerktoejet registrerer og lægger paa turen."""
    kaldt: dict[str, dict] = {}

    def falsk_register(**kw):
        kaldt["register"] = kw
        return "aid-video-1"

    def falsk_note(turn_id, **kw):
        kaldt["note"] = {"turn_id": turn_id, **kw}

    import core.services.attachment_service as A
    import core.services.published_files as F
    monkeypatch.setattr(A, "register_generated_media", falsk_register)
    monkeypatch.setattr(F, "note", falsk_note)
    return kaldt


def _ok_video(**over):
    svar = {
        "status": "ok", "generation_id": "g1", "path": "/tmp/klip.mp4",
        "bytes": 1234, "content_type": "video/mp4", "model": "sora",
    }
    svar.update(over)
    return svar


def test_video_registreres_som_attachment(monkeypatch, fanget):
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    ud = P._exec_pollinations_video({"prompt": "en kat"})
    assert ud["status"] == "ok"
    assert fanget["register"]["local_path"] == "/tmp/klip.mp4"
    assert fanget["register"]["mime_type"] == "video/mp4"


def test_video_laegges_paa_TUREN(monkeypatch, fanget):
    """Registreringen alene goer den hentbar; posten goer den synlig."""
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    P._exec_pollinations_video({"prompt": "en kat", "_runtime_turn_id": "turn-7"})
    note = fanget["note"]
    assert note["turn_id"] == "turn-7"
    assert note["filename"] == "klip.mp4"
    assert note["mime_type"] == "video/mp4"
    assert note["attachment_id"] == "aid-video-1"
    assert note["size_bytes"] == 1234


def test_attachment_id_kommer_MED_i_svaret(monkeypatch, fanget):
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    ud = P._exec_pollinations_video({"prompt": "en kat"})
    assert ud["attachment_id"] == "aid-video-1"


def test_en_registrering_der_fejler_vaelter_ikke_genereringen(monkeypatch):
    """Ti minutters arbejde maa ikke gaa tabt fordi en DB-raekke ikke kunne skrives."""
    import core.services.attachment_service as A
    import core.services.published_files as F
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    monkeypatch.setattr(A, "register_generated_media",
                        lambda **kw: (_ for _ in ()).throw(RuntimeError("db nede")))
    monkeypatch.setattr(F, "note", lambda *a, **k: None)
    ud = P._exec_pollinations_video({"prompt": "en kat"})
    assert ud["status"] == "ok"
    assert ud["path"] == "/tmp/klip.mp4"
    assert ud["attachment_id"] == ""      # aerligt tomt, ikke opdigtet


def test_en_note_der_fejler_vaelter_heller_ikke(monkeypatch):
    import core.services.attachment_service as A
    import core.services.published_files as F
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    monkeypatch.setattr(A, "register_generated_media", lambda **kw: "aid-1")
    monkeypatch.setattr(F, "note",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    ud = P._exec_pollinations_video({"prompt": "en kat"})
    assert ud["status"] == "ok" and ud["attachment_id"] == "aid-1"


def test_en_FEJLET_generering_registrerer_ingenting(monkeypatch, fanget):
    monkeypatch.setattr(P, "generate_video",
                        lambda **kw: {"status": "error", "text": "provider nede"})
    ud = P._exec_pollinations_video({"prompt": "en kat"})
    assert ud["status"] == "error"
    assert "register" not in fanget and "note" not in fanget


def test_uden_prompt_naar_vi_slet_ikke_providere(monkeypatch, fanget):
    monkeypatch.setattr(P, "generate_video",
                        lambda **kw: pytest.fail("maatte ikke kalde provideren"))
    assert P._exec_pollinations_video({"prompt": "  "})["status"] == "error"


def test_video_faar_SAMME_behandling_som_et_billede(monkeypatch):
    """Det er hele kravet. En test der kun saa paa video kunne ikke opdage at
    de to grene drev fra hinanden igen."""
    set_af_kald: dict[str, set] = {}

    def spor(navn):
        def f(**kw):
            set_af_kald.setdefault(navn, set()).add("register")
            return "aid"
        return f

    import core.services.attachment_service as A
    import core.services.published_files as F
    for navn, gen, kald in (
        ("billede", "generate_image",
         lambda: P._exec_pollinations_image({"prompt": "x", "_runtime_turn_id": "t"})),
        ("video", "generate_video",
         lambda: P._exec_pollinations_video({"prompt": "x", "_runtime_turn_id": "t"})),
    ):
        noter: list = []
        monkeypatch.setattr(P, gen, lambda **kw: _ok_video(
            content_type="image/jpeg" if navn == "billede" else "video/mp4"))
        monkeypatch.setattr(A, "register_generated_media", spor(navn))
        monkeypatch.setattr(A, "register_generated_image", spor(navn))
        monkeypatch.setattr(F, "note", lambda t, **kw: noter.append(kw))
        ud = kald()
        assert "register" in set_af_kald.get(navn, set()), f"{navn} registrerede ikke"
        assert noter, f"{navn} lagde intet paa turen"
        assert ud.get("attachment_id") is not None, f"{navn} svarede uden attachment_id"


def test_videoen_baerer_sit_kald_id_saa_den_lander_rigtigt(monkeypatch):
    """Uden ankeret ryger videoen bagest, efter prosaen. Billederne havde
    praecis den fejl indtil 13/9-2026."""
    noter: list = []
    import core.services.attachment_service as A
    import core.services.published_files as F
    monkeypatch.setattr(P, "generate_video", lambda **kw: _ok_video())
    monkeypatch.setattr(A, "register_generated_media", lambda **kw: "aid")
    monkeypatch.setattr(F, "note", lambda t, **kw: noter.append(kw))
    P._exec_pollinations_video({"prompt": "x", "_runtime_tool_use_id": "call_42"})
    assert noter[0]["tool_use_id"] == "call_42"


# ── Video-redigering (28/9-2026) ────────────────────────────────────────────
#
# Kapabiliteten FINDES: pollinations' video-endpoint tager `reference_videos`
# («public HTTP(S) video URLs for motion or style guidance»), og fem af nitten
# video-modeller oplyser evnen i deres `video_capabilities`.
#
# Men ordet er **public**. Udbyderen henter selv videoen. Jarvis' egne filer
# ligger bag /attachments/ og /files/, som begge svarede 401 uden token da det
# blev maalt paa CT105. Derfor kan vaerktoejet redigere en video fra nettet,
# men ikke en han lige har lavet — og det skal det SIGE, ikke gaette.


def test_en_lokal_sti_afvises_med_en_forklaring():
    """Sendte vi stien alligevel, ville udbyderen faa 401 og svare med en HELT
    ny video der intet havde med originalen at goere. Det ligner et resultat."""
    ud = P.edit_video(prompt="gør den blå", video_url="/home/bs/klip.mp4")
    assert ud["status"] == "error"
    assert "public" in ud["text"].lower() or "OFFENTLIG" in ud["text"]


def test_en_attachments_adresse_afvises_ogsaa():
    ud = P.edit_video(prompt="x", video_url="/attachments/media/aid-1")
    assert ud["status"] == "error"


def test_uden_video_url_er_der_intet_at_redigere():
    assert P.edit_video(prompt="x", video_url="")["status"] == "error"


def test_en_offentlig_url_naar_frem_til_udbyderen(monkeypatch):
    fanget: dict = {}
    monkeypatch.setattr(P, "_hent_video",
                        lambda **kw: fanget.update(kw) or _ok_video())
    monkeypatch.setattr(P, "_api_key", lambda: "n")
    P.edit_video(prompt="gør den blå", video_url="https://example.com/k.mp4")
    assert "reference_videos=https%3A%2F%2Fexample.com%2Fk.mp4" in fanget["url"]


def test_kun_modeller_der_FAKTISK_kan_video_til_video(monkeypatch):
    """De oevrige fjorten ignorerer `reference_videos` TAVST og returnerer en
    ny video. En tavs ignorering er vaerre end en fejl — den ligner et svar."""
    fanget: dict = {}
    monkeypatch.setattr(P, "_hent_video", lambda **kw: fanget.update(kw) or _ok_video())
    monkeypatch.setattr(P, "_api_key", lambda: "n")
    for duer_ikke in ("wan-fast", "veo", "nova-reel", "p-video"):
        P.edit_video(prompt="x", video_url="https://e.com/k.mp4", model=duer_ikke)
        assert fanget["model"] == P._DEFAULT_VIDEO_EDIT_MODEL, duer_ikke
    for duer in P._VIDEO_EDIT_MODELS:
        P.edit_video(prompt="x", video_url="https://e.com/k.mp4", model=duer)
        assert fanget["model"] == duer


def test_en_redigeret_video_registreres_som_enhver_anden(monkeypatch, fanget):
    """Den skal i traaden paa samme maade — ellers er den lige saa usynlig som
    en genereret video var foer i dag."""
    monkeypatch.setattr(P, "_api_key", lambda: "n")
    monkeypatch.setattr(P, "_hent_video", lambda **kw: _ok_video())
    ud = P._exec_pollinations_video_edit({
        "prompt": "gør den blå", "video_url": "https://e.com/k.mp4",
        "_runtime_turn_id": "turn-9", "_runtime_tool_use_id": "call_9",
    })
    assert ud["status"] == "ok" and ud["attachment_id"] == "aid-video-1"
    assert fanget["note"]["tool_use_id"] == "call_9"
    assert fanget["register"]["mime_type"] == "video/mp4"
    assert "edited" in ud["text"].lower()


def test_uden_api_noegle_siger_den_det(monkeypatch):
    monkeypatch.setattr(P, "_api_key", lambda: "")
    ud = P.edit_video(prompt="x", video_url="https://e.com/k.mp4")
    assert ud["status"] == "error" and "api_key" in ud["text"]


def test_vaerktoejet_er_REGISTRERET_saa_han_kan_kalde_det():
    """Et vaerktoej ingen kan kalde er en funktion, ikke en kapabilitet."""
    from core.tools.simple_tools import _TOOL_HANDLERS
    assert "pollinations_video_edit" in _TOOL_HANDLERS
    navne = [d["function"]["name"] for d in P.POLLINATIONS_TOOL_DEFINITIONS]
    assert "pollinations_video_edit" in navne


def test_beskrivelsen_ADVARER_om_graensen():
    """Modellen laeser kun beskrivelsen. Staar graensen der ikke, vil den
    proeve med sin egen fil og faa noget der ligner et svar."""
    d = next(x for x in P.POLLINATIONS_TOOL_DEFINITIONS
             if x["function"]["name"] == "pollinations_video_edit")
    besk = d["function"]["description"].lower()
    assert "public" in besk
    assert "cannot" in besk or "not" in besk
