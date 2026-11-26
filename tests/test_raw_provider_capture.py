"""Vagt for raw_provider_capture (26/11-2026).

Modulet findes fordi vi har 26.558 NORMALISEREDE payloads men nul
observationer af udbyderens faktiske protokol. Det kan ikke afgøre om
provideren sender et felt vi kaster — og det spørgsmål blokerer hele
arbejdet med et leveringssignal.

Vagterne her bevogter de fire ting der gør målingen meningsfuld:

1. Capture sidder FØR adapterens ``startswith("data: ")``-filter, så
   ikke-data-events bliver set. Går den galt, måler vi intet nyt.
2. Nøgler og tokens redigeres før skrivning.
3. Skemaet registrerer FORMEN (nøglestier), ikke værdierne — så
   «findes der et channel-felt?» kan besvares uden at læse payloads.
4. Slukket koster det nul, og et fejlende capture må aldrig vælte en tur.
"""
from __future__ import annotations

import json

import pytest

from core.services import raw_provider_capture as rpc


@pytest.fixture()
def capture_dir(tmp_path, monkeypatch):
    """Isolér fil-stierne pr. test — modulet skriver ellers til /tmp."""
    d = tmp_path / "raw"
    monkeypatch.setattr(rpc, "_DIR", str(d))
    monkeypatch.setattr(rpc, "_CAPTURE", str(d / "capture.jsonl"))
    monkeypatch.setattr(rpc, "_SKEMA", str(d / "skema.json"))
    rpc._skema.clear()
    rpc._siden_flush = 0
    return d


def _linjer(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(l) for l in fh if l.strip()]


def test_armeret_foelger_sentinel(tmp_path, monkeypatch):
    sentinel = tmp_path / "sentinel"
    monkeypatch.setattr(rpc, "_SENTINEL", str(sentinel))
    assert rpc.armeret() is False
    sentinel.write_text("", encoding="utf-8")
    assert rpc.armeret() is True


def test_ikke_data_linje_fanges_altid(capture_dir):
    """KERNEN: adapteren kaster alt der ikke starter med 'data: '. Vi må ikke.

    En udbyder der sender ``event: delivery`` ville ellers være usynlig for
    os — og det er præcis det signal vi leder efter.
    """
    rpc.noter_linje(
        provider="deepseek", model="m", linje="event: delivery", linje_nr=500
    )
    post = _linjer(capture_dir / "capture.jsonl")
    assert len(post) == 1
    assert post[0]["linje"] == "event: delivery"


def test_afgraensning_efter_loft(capture_dir):
    """Efter loftet gemmes kun protokol-bærende linjer, ikke ren tekststøj."""
    rpc.noter_linje(provider="p", model="m", linje='data: {"a":1}', linje_nr=1)
    # Ren content-linje langt inde i streamen: støj, skal ikke med.
    rpc.noter_linje(
        provider="p", model="m", linje='data: {"choices":[{"delta":{"content":"x"}}]}',
        linje_nr=500,
    )
    # Usage-chunk langt inde: protokol, skal med.
    rpc.noter_linje(
        provider="p", model="m", linje='data: {"usage":{"prompt_tokens":5}}',
        linje_nr=501,
    )
    linjer = [p["linje"] for p in _linjer(capture_dir / "capture.jsonl")]
    assert len(linjer) == 2
    assert "usage" in linjer[1]


def test_api_noegle_redigeres(capture_dir):
    """En nøgle må aldrig lande i en fil der læses bredt."""
    rpc.noter_linje(
        provider="p", model="m",
        linje='data: {"key": "sk-abcdefghijklmnopqrstuvwx"}', linje_nr=1,  # pragma: allowlist secret
    )
    post = _linjer(capture_dir / "capture.jsonl")[0]
    assert "sk-abcdefghijklmnopqrstuvwx" not in post["linje"]  # pragma: allowlist secret
    assert "[REDAKTERET_API_KEY]" in post["linje"]


def test_lang_linje_klippes(capture_dir):
    rpc.noter_linje(
        provider="p", model="m", linje="data: " + "a" * 10_000, linje_nr=1
    )
    post = _linjer(capture_dir / "capture.jsonl")[0]
    assert len(post["linje"]) <= rpc._MAX_BYTES_PR_LINJE + 20
    assert post["linje"].endswith("[KLIPPET]")


def test_skema_registrerer_noeglesti_ikke_vaerdi(capture_dir):
    """Skemaet skal kunne svare på 'findes feltet?' uden at gemme indholdet."""
    rpc.noter_event(
        provider="deepseek", model="m",
        event={
            "choices": [{"delta": {"content": "hemmelig tekst", "channel": "delivery"}}],
            "usage": {"prompt_tokens": 3},
        },
    )
    rpc.afslut_kald()
    skema = rpc.skema_rapport()
    stier = set(skema["deepseek"])
    assert "choices[].delta.channel:str" in stier
    assert "choices[].delta.content:str" in stier
    assert "usage.prompt_tokens:int" in stier
    # Værdierne må ikke være i skemaet — kun formen.
    raa = json.dumps(skema)
    assert "hemmelig tekst" not in raa
    assert "delivery" not in raa


def test_skema_er_provider_adskilt(capture_dir):
    """Et felt der kun findes hos én udbyder må ikke drukne i en anden."""
    rpc.noter_event(provider="deepseek", model="m", event={"a": 1})
    rpc.noter_event(provider="ollama", model="m", event={"b": 1})
    rpc.afslut_kald()
    skema = rpc.skema_rapport()
    assert "a:int" in skema["deepseek"]
    assert "b:int" not in skema["deepseek"]
    assert "b:int" in skema["ollama"]


def test_skema_flusher_ved_kald_slut(capture_dir):
    """En kort stream (< flush-intervallet) må ikke efterlade skemaet tomt."""
    rpc.noter_event(provider="p", model="m", event={"x": 1})
    rpc.afslut_kald()
    assert (capture_dir / "skema.json").exists()


def test_kaster_aldrig_selv_om_stien_er_doed(capture_dir, monkeypatch):
    """Et fejlende capture må ikke vælte en tur. Tavshed er den rigtige vej."""
    monkeypatch.setattr(rpc, "_DIR", "/proc/umulig/sti")
    monkeypatch.setattr(rpc, "_CAPTURE", "/proc/umulig/sti/capture.jsonl")
    rpc.noter_linje(provider="p", model="m", linje="data: {}", linje_nr=1)
    rpc.noter_event(provider="p", model="m", event={"a": 1})
    rpc.afslut_kald()  # må ikke kaste


def test_ende_til_ende_gennem_den_rigtige_stream(capture_dir, monkeypatch, tmp_path):
    """KÆDEN, ikke bare modulet: en udbyder der sender et ukendt felt skal ses.

    Dette er den test der afgør om målingen overhovedet er mulig. Modulet kan
    være nok så korrekt — hvis wiringen sidder efter adapterens
    ``startswith("data: ")``, er et ``event:``-felt eller et ``channel``-felt
    stadig usynligt, og så kan vi ikke falsificere «provideren sender et
    signal vi kaster».
    """
    from contextlib import contextmanager

    import core.services.cheap_provider_runtime as cheap
    import core.services.cheap_provider_runtime_streaming as streaming

    sentinel = tmp_path / "sentinel"
    sentinel.write_text("", encoding="utf-8")
    monkeypatch.setattr(rpc, "_SENTINEL", str(sentinel))

    class _FakeResponse:
        status_code = 200
        headers: dict = {}

        def __init__(self, lines):
            self._lines = list(lines)

        def iter_lines(self):
            return iter(self._lines)

        def iter_bytes(self):
            return iter(l.encode() for l in self._lines)

    linjer = [
        ": keepalive",
        "event: delivery",
        'data: {"model":"m","choices":[{"delta":{"content":"Hej","channel":"delivery"}}]}',
        'data: {"choices":[{"delta":{"reasoning_content":"taenker"}}]}',
        'data: {"usage":{"prompt_tokens":5,"completion_tokens":2},"choices":[]}',
        "data: [DONE]",
    ]

    @contextmanager
    def fake_stream(method, url, *, json=None, headers=None, timeout=None):  # noqa: A002
        yield _FakeResponse(linjer)

    monkeypatch.setattr(streaming.httpx, "stream", fake_stream)
    monkeypatch.setattr(
        cheap, "_require_credentials",
        lambda **kw: {"api_key": "fake-test-key"}, raising=False,  # pragma: allowlist secret
    )
    monkeypatch.setattr(
        cheap, "provider_runtime_defaults",
        lambda pid: {"base_url": "https://api.test/v1"}, raising=False,
    )

    list(streaming._iter_openai_compatible_chat_events(
        provider="deepseek", model="m", auth_profile="default",
        base_url="https://api.test/v1",
        messages=[{"role": "user", "content": "hej"}],
    ))

    fangede = [p["linje"] for p in _linjer(capture_dir / "capture.jsonl")]
    # 1. Ikke-data-linjerne — dem adapteren kaster uden at nogen spørger.
    assert ": keepalive" in fangede
    assert "event: delivery" in fangede
    # 2. Det ukendte felt står i det rå event, ikke kun i skemaet.
    assert any('"channel"' in l for l in fangede)
    # 3. Og skemaet registrerede det som en nøglesti.
    assert "choices[].delta.channel:str" in set(rpc.skema_rapport()["deepseek"])


def test_sentinel_og_mappe_er_forskellige_stier():
    """Sentinel er en FIL, mappen er en MAPP. Sammenfald gjorde målingen blind.

    Målt 26/11-2026: begge hed `/tmp/jarvis-raw-provider`. `touch` oprettede
    en fil, `os.makedirs` fejlede på den samme sti, self-safe'en slugte det —
    og der blev skrevet NUL mens `armeret()` svarede True. Uden denne vagt
    ville næste runde igen «måle» ingenting og kalde det et resultat.
    """
    assert rpc._DIR != rpc._SENTINEL, "mappen må ikke være samme sti som sentinel-filen"
    assert not rpc._CAPTURE.startswith(rpc._SENTINEL + "/")


def test_skrivefejl_siges_hoejt_én_gang(capture_dir, monkeypatch, capsys):
    """Self-safe må ikke betyde self-blind: en umulig sti skal siges højt."""
    monkeypatch.setattr(rpc, "_DIR", "/proc/umulig/sti")
    monkeypatch.setattr(rpc, "_CAPTURE", "/proc/umulig/sti/capture.jsonl")
    monkeypatch.setattr(rpc, "_advarsel_givet", False)
    rpc.noter_linje(provider="p", model="m", linje="data: {}", linje_nr=1)
    rpc.noter_linje(provider="p", model="m", linje="data: {}", linje_nr=2)
    err = capsys.readouterr().err
    assert "SKRIVER IKKE" in err
    # Netop ÉN gang — ellers drukner advarslen i sig selv ved hver linje.
    assert err.count("SKRIVER IKKE") == 1
