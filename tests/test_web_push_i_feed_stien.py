# tests/test_web_push_i_feed_stien.py
"""Feed-stien skal naa web-push (7/11-2026).

## Hvorfor denne fil findes

Målt 7/11-2026, efter at `_push_to_web` fik telemetri (commit fad825468):
**43 `run_done` i feeden, kun 4 `push.web_sent`** — alle til Bjørn, alle fra
rutine-stien. Nul til Mikkel, nul til Michelle. Og nul `push.web_skipped` /
`push.web_failed`, hvilket er det afgørende spor: funktionen blev **aldrig
kaldt**. Havde brugerne manglet abonnementer, ville `skipped` have stået der.

Rodårsag: `_deliver_to_channel` (notification_router.py) kaldte ved
`mobile`/`push` kun `pd._push_to_user` (FCM), og ved `auto` kun
`route_device_aware` — som selv ender i `_send_fcm`/`_send_desktop`. Web-push
fandtes udelukkende i `push_dispatcher._route_or_blast`, som feed-stien aldrig
rammer.

## Hvad testene maaler

Ikke at funktionen `_push_to_web` virker — det gør den, og det er maalt mod
den levende DB. De maaler **koblingen**: at routerens transportlag faktisk
kalder den. En test paa funktionen alene ville vaere groen selv om koblingen
manglede, og det er praecis den fejlform der kostede fire runder i november.
"""
from __future__ import annotations


def _router_med_mocket_transport(monkeypatch):
    """Routeren med quiet hours slaaet fra og web-push fanget."""
    import core.services.notification_router as nr
    from core.services import push_dispatcher as pd

    kaldt = {"web": [], "fcm": [], "device": []}

    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)
    monkeypatch.setattr(pd, "_push_to_web",
                        lambda uid, data: kaldt["web"].append((uid, data)) or True)
    monkeypatch.setattr(pd, "_push_to_user",
                        lambda uid, data: kaldt["fcm"].append((uid, data)) or True)
    monkeypatch.setattr(nr, "route_device_aware",
                        lambda uid, payload, kind: kaldt["device"].append((uid, kind)))
    return nr, kaldt


def test_auto_kanalen_naar_web_push(isolated_runtime, monkeypatch) -> None:
    """`auto` er den kanal `run_done` lander i: `STANDARD["run_done"] = "auto"`,
    og `resolve_channel` falder tilbage til brugerens `global` (default "auto").

    Web-abonnementer er ikke i device-rangeringen — en browser kan ikke melde
    presence som en app — saa de skal have beskeden uanset hvilken enhed
    rangeringen vaelger. Det er samme politik som `_route_or_blast`.
    """
    nr, kaldt = _router_med_mocket_transport(monkeypatch)

    res = nr.route_proactive_notification(
        "bjorn", "run_done", {"title": "Svar klar", "body": "hej"}, importance="normal")

    assert res["delivered"] is True
    assert kaldt["web"], (
        "feed-stien naaede ALDRIG web-push — det var hele fejlen maalt 7/11: "
        "43 run_done i feeden, 4 push.web_sent, nul skipped"
    )
    assert kaldt["device"], "device-routing skal stadig koere ved siden af"


def test_mobile_kanalen_naar_BADE_fcm_og_web(isolated_runtime, monkeypatch) -> None:
    """Ved et eksplicit `mobile`-valg skal FCM stadig bruges — web-push kommer
    oveni, ikke i stedet. En browser kan ikke melde presence, saa den kan
    ikke vaelges bort af rangeringen."""
    from core.services import notifikations_valg as v

    nr, kaldt = _router_med_mocket_transport(monkeypatch)
    v.saet("bjorn", "run_done", "mobile")

    nr.route_proactive_notification(
        "bjorn", "run_done", {"title": "Svar klar", "body": "hej"}, importance="normal")

    assert kaldt["fcm"], "FCM skal stadig leveres naar brugeren har valgt mobile"
    assert kaldt["web"], "web-abonnementet skal have beskeden uanset FCM"


def test_web_push_naar_ikke_fcm_er_registreret(isolated_runtime, monkeypatch) -> None:
    """Michelle har kun et Apple-web-abonnement (ingen FCM-token maalt 7/11).
    Uden web-grenen i `mobile`/`push` ville hun aldrig faa noget, mens
    routeren meldte «delivered: False» uden at nogen kunne se hvorfor."""
    import core.services.notification_router as nr
    from core.services import notifikations_valg as v
    from core.services import push_dispatcher as pd

    monkeypatch.setattr(nr, "is_quiet_hours", lambda *a, **k: False)
    monkeypatch.setattr(pd, "_push_to_user", lambda uid, data: False)  # ingen FCM-token
    web = []
    monkeypatch.setattr(pd, "_push_to_web", lambda uid, data: web.append(uid) or True)
    v.saet("bjorn", "run_done", "mobile")

    res = nr.route_proactive_notification(
        "bjorn", "run_done", {"title": "Svar klar", "body": "hej"}, importance="normal")

    assert web, "kun web-abonnementet findes — saa skal det vaere den vej der bruges"
    assert res["delivered"] is True, (
        "en leverance der naaede web-abonnementet maa ikke meldes som fejlet"
    )


def test_ingen_web_push_naar_slags_er_fravalgt(isolated_runtime, monkeypatch) -> None:
    """Vaernet mod det modsatte: et eksplicit «ingen» skal stadig betyde INGEN
    push. Fixet maa ikke goere brugerens fravalg virkningsloest."""
    from core.services import notifikations_valg as v

    nr, kaldt = _router_med_mocket_transport(monkeypatch)
    v.saet("bjorn", "run_done", "ingen")

    res = nr.route_proactive_notification(
        "bjorn", "run_done", {"title": "Svar klar", "body": "hej"}, importance="normal")

    assert res["channel"] == "fravalgt"
    assert kaldt["web"] == [], "brugeren har slaaet slags'en fra — den maa ikke pushes"
