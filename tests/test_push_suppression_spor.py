# tests/test_push_suppression_spor.py
"""Suppressionen skal efterlade et spor (7/11-2026).

## Hvorfor denne fil findes

Målt 7/11-2026 kl. 13:41:14 i den levende DB: et `push.web_sent` med
`kind: run_done` havde **tomt `run_id`**, selv om notifikationen samme sekund
havde `ref=autonomous-0c6c92db…`. To ting var galt på én gang:

1. `_maaske_push` byggede payloaden uden `run_id`, så `_push_to_web` skrev
   tomt i hver eneste `push.web_*`-række fra feed-stien. Pushet kunne ikke
   knyttes til det run det gjaldt.
2. Suppressionen (`was_consumed_or_active`) returnerede **uden** at skrive
   noget. «Undertrykt» og «aldrig kaldt» så derfor ens i journalen — samme
   tavshed som telemetri-fixet 6/11 skulle afskaffe, blot et lag længere inde.

## Hvad testene måler

Koblingen mellem `_maaske_push` og telemetrien — ikke at `_push_to_web` selv
virker (det er målt mod den levende DB). En test på funktionen alene ville
være grøn selv om payloaden aldrig fik `run_id` med.
"""
from __future__ import annotations


def _fang_events(monkeypatch):
    """Fanger alt hvad `_push_event` skriver, uden at røre eventbus."""
    import core.services.push_dispatcher as pd

    skrevet: list[tuple[str, dict]] = []
    monkeypatch.setattr(pd, "_push_event",
                        lambda kind, payload: skrevet.append((kind, dict(payload))))
    return skrevet


def test_run_id_foelger_med_i_payloaden(isolated_runtime, monkeypatch) -> None:
    """`ref` ER run-id'et for run_done. Uden det kan pushet ikke spores.

    Målt 7/11-2026: notifikationen havde `ref=autonomous-0c6c92db…`, pushet
    havde `run_id: ""`. Sporet pegede på intet.
    """
    from core.services import notifikations_emittere as e
    from core.services import notification_router as nr

    set_payload: list[dict] = []
    monkeypatch.setattr(nr, "route_proactive_notification",
                        lambda uid, slags, payload, **kw: set_payload.append(dict(payload)) or {"ok": True})
    # Runnet er IKKE set live -> suppressionen maa ikke fyre.
    from core.services import run_event_log as rel
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: False)

    e.paa_koersel_faerdig("visible-abc123", user_id="bjorn",
                          session_id="s-1", titel="Test")

    assert set_payload, "pushet blev slet ikke forsøgt — så beviser testen intet"
    assert set_payload[0].get("run_id") == "visible-abc123", (
        "run_id manglede i payloaden — så kan push.web_*-rækken ikke knyttes "
        "til det run den gjaldt (målt 7/11: tomt run_id i den levende DB)"
    )


def test_suppression_efterlader_seen_live_spor(isolated_runtime, monkeypatch) -> None:
    """Et undertrykt push skal skrive `push.web_skipped` med reason=seen_live.

    Uden sporet kan ingen — heller ikke jeg — afgøre om suppressionen fyrede
    eller om funktionen aldrig blev kaldt. Det var præcis den tavshed der
    gjorde gårsdagens fejlsøgning blind.
    """
    from core.services import notifikations_emittere as e
    from core.services import notification_router as nr
    from core.services import run_event_log as rel

    skrevet = _fang_events(monkeypatch)
    kaldt: list = []
    monkeypatch.setattr(nr, "route_proactive_notification",
                        lambda *a, **kw: kaldt.append(a) or {"ok": True})
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: True)

    e.paa_koersel_faerdig("visible-setlive", user_id="bjorn",
                          session_id="s-1", titel="Test")

    assert not kaldt, "pushet skulle være undertrykt — brugeren sad og så svaret"
    assert skrevet, (
        "suppressionen returnerede UDEN at skrive et spor — så ser «undertrykt» "
        "og «aldrig kaldt» ens ud i journalen"
    )
    kind, payload = skrevet[0]
    assert kind == "push.web_skipped"
    assert payload.get("reason") == "seen_live"
    assert payload.get("run_id") == "visible-setlive", (
        "sporet skal navngive det run der blev undertrykt, ellers kan det "
        "ikke efterprøves"
    )


def test_ikke_set_live_giver_ingen_skip_raekke(isolated_runtime, monkeypatch) -> None:
    """Modstykket: et run der IKKE er set live må ikke skrive en skip-række.

    Uden denne kunne jeg «bevise» suppressionen ved at skrive sporet i alle
    tilfælde — og så målte rækken ingenting.
    """
    from core.services import notifikations_emittere as e
    from core.services import notification_router as nr
    from core.services import run_event_log as rel

    skrevet = _fang_events(monkeypatch)
    monkeypatch.setattr(nr, "route_proactive_notification",
                        lambda *a, **kw: {"ok": True})
    monkeypatch.setattr(rel, "was_consumed_or_active", lambda rid: False)

    e.paa_koersel_faerdig("visible-ikke-set", user_id="bjorn",
                          session_id="s-1", titel="Test")

    assert not [s for s in skrevet if s[1].get("reason") == "seen_live"], (
        "der blev skrevet en seen_live-skip for et run der IKKE var set live"
    )
