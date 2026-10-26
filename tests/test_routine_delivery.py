def test_delivery_service_has_no_session_surface():
    from core.services.routine_delivery import RoutineDeliveryService

    assert not hasattr(RoutineDeliveryService(), "session_id")


# ── Push til ejeren (25/10-2026) ────────────────────────────────────────────
# ``desk`` betoed kun «resultatet kan hentes». Maalt den dag: Michelles rutine
# blev ``delivered`` uden at hendes telefon fik noget, fordi der slet ikke
# fandtes en kobling mellem rutine-delivery og push-stakken. Disse tests laaser
# koblingen — og de fire vaern der goer den sikker.

#: Michelles to noegler — de er IKKE ens, og det er hele pointen:
#: rutinen ejes af det kanoniske id, abonnementet ligger under Discord-id'et.
KANONISK = "28ef63fb85cf5561b97f496c3ff98cad"  # pragma: allowlist secret
DISCORD = "1313522677369143429"


def _claim(owner=KANONISK, run_id="run_test"):  # pragma: allowlist secret
    from core.services.routine_delivery import DeliveryClaim

    return DeliveryClaim(
        delivery_id="delivery_test", run_id=run_id, owner_user_id=owner,
        channel="desk", status="delivered", retry_count=0, lease_generation=1,
    )


def _opsæt(monkeypatch, *, routine=None, account=None):
    """Stub DB- og kontolag; returnér listen af push-kald."""
    from core.runtime import db_routines
    import core.services.push_dispatcher as pd

    kald: list[tuple[str, dict]] = []
    monkeypatch.setattr(
        db_routines, "get_run",
        lambda run_id: {"run_id": run_id, "routine_id": "routine_test"},
    )
    monkeypatch.setattr(
        db_routines, "get_routine",
        lambda routine_id, decrypt_for=None: routine,
    )
    monkeypatch.setattr(pd, "_push_to_web", lambda uid, data: kald.append((uid, data)) or True)
    if account is not None:
        from core.identity import user_db
        monkeypatch.setattr(user_db, "get_user", lambda uid: account)
    return kald


def test_push_gaar_til_discord_id_ikke_kanonisk(monkeypatch):
    """De to lag bruger forskellige noegler — den fejl kostede en hel dag."""
    kald = _opsæt(
        monkeypatch,
        routine={"name": "Ugentlige madopskrifter", "access_scope": "user_private",
                 "delivery_policy": {"channel": "desk"}},
        account={"user_id": KANONISK,
                 "discord_id": DISCORD},
    )
    from core.services.routine_delivery import _push_owner

    _push_owner(_claim())

    assert len(kald) == 1
    assert kald[0][0] == DISCORD
    assert kald[0][0] != KANONISK


def test_push_baerer_navn_ikke_resultat(monkeypatch):
    """Resultatet lever paa rutinens flade — pushen maa ikke kopiere det."""
    kald = _opsæt(
        monkeypatch,
        routine={"name": "Ugentlige madopskrifter", "access_scope": "user_private",
                 "delivery_policy": {"channel": "desk"}},
        account={"discord_id": DISCORD},
    )
    from core.services.routine_delivery import _push_owner

    _push_owner(_claim())

    data = kald[0][1]
    assert data["title"] == "Ugentlige madopskrifter"
    assert data["run_id"] == "run_test"
    assert "opskrift" not in data["body"].lower()


def test_system_rutine_pusher_ikke(monkeypatch):
    """Heartbeat/dream er rammer, ikke opgaver — de skal ikke vaekke en telefon."""
    kald = _opsæt(
        monkeypatch,
        routine={"name": "heartbeat", "access_scope": "system_owner",
                 "delivery_policy": {}},
        account={"discord_id": DISCORD},
    )
    from core.services.routine_delivery import _push_owner

    _push_owner(_claim())

    assert kald == []


def test_push_false_i_policy_slaar_fra(monkeypatch):
    kald = _opsæt(
        monkeypatch,
        routine={"name": "Stille rutine", "access_scope": "user_private",
                 "delivery_policy": {"channel": "desk", "push": False}},
        account={"discord_id": DISCORD},
    )
    from core.services.routine_delivery import _push_owner

    _push_owner(_claim())

    assert kald == []


def test_uden_discord_mapping_pusher_ikke(monkeypatch):
    """En konto uden Discord-id har intet abonnement at sende til."""
    kald = _opsæt(
        monkeypatch,
        routine={"name": "Rutine", "access_scope": "user_private",
                 "delivery_policy": {}},
        account={"user_id": KANONISK, "discord_id": ""},
    )
    from core.services.routine_delivery import _push_owner

    _push_owner(_claim())

    assert kald == []


def test_push_fejl_vaelter_ikke_leveringen(monkeypatch):
    """Self-safe: en brækket push maa ikke goere en leveret rutine fejlet."""
    from core.runtime import db_routines
    import core.services.push_dispatcher as pd
    from core.services.routine_delivery import _push_owner

    monkeypatch.setattr(
        db_routines, "get_run",
        lambda run_id: {"run_id": run_id, "routine_id": "routine_test"},
    )
    monkeypatch.setattr(
        db_routines, "get_routine",
        lambda routine_id, decrypt_for=None: {
            "name": "Rutine", "access_scope": "user_private", "delivery_policy": {},
        },
    )
    from core.identity import user_db
    monkeypatch.setattr(
        user_db, "get_user", lambda uid: {"discord_id": DISCORD},
    )

    def boom(uid, data):
        raise RuntimeError("push-tjenesten er nede")

    monkeypatch.setattr(pd, "_push_to_web", boom)

    _push_owner(_claim())  # maa ikke kaste


# ── Lag 3: resultatet skal lande i ejerens EGEN session (26/10-2026) ──────
#
# Maalt 26/10-2026: rutinen koerte, pushede, og resultatet laa i
# `routine_runs.result_enc` — men der var intet sted at laese det. Bjørn:
# «der findes ikk en session, kun push». Leverancen var gjort session-neutral
# med vilje, fordi `most_recent_session_id()` ikke har noget bruger-scope og
# derfor ville skrive til en FREMMED session. Scopet findes nu.


def test_resultatet_laegges_i_ejerens_egen_session(monkeypatch):
    """Uden dekryptering er `result` tom — og saa leveres der intet.

    Det var den faktiske fejl: `get_run` uden `decrypt_for` giver blob, ikke
    tekst, og funktionen faldt tavst igennem.
    """
    from core.services import routine_delivery as rd

    kaldt = {}

    class _FakeInbox:
        @staticmethod
        def is_session_active(sid):
            return True

        @staticmethod
        def enqueue(**kw):
            kaldt.update(kw)
            return {"status": "queued", "id": 1}

    import core.services.session_inbox as si
    monkeypatch.setattr(si, "is_session_active", _FakeInbox.is_session_active)
    monkeypatch.setattr(si, "enqueue", _FakeInbox.enqueue)
    monkeypatch.setattr(
        "core.services.chat_sessions.most_recent_session_id_for_user",
        lambda uid: "chat-ejer-session",
    )
    monkeypatch.setattr(
        rd.db_routines, "get_run",
        lambda run_id, decrypt_for=None: {
            "run_id": run_id, "routine_id": "r1",
            "result": b"Tre opskrifter: boller i karry",
        },
    )
    monkeypatch.setattr(
        rd.db_routines, "get_routine",
        lambda rid, decrypt_for=None: {
            "name": "Ugentlige madopskrifter",
            "access_scope": "user_private",
            "delivery_policy": {},
            "workspace_name": None,
        },
    )

    rd._deliver_to_session(rd.DeliveryClaim(
        delivery_id="d1", run_id="run-1", owner_user_id="michelle",
        channel="desk", status="delivering", retry_count=0, lease_generation=1,
    ))

    assert kaldt.get("session_id") == "chat-ejer-session"
    assert "boller i karry" in kaldt.get("content", "")
    # bytes skal vaere afkodet — ellers lander der b'...' i chatten
    assert "b'" not in kaldt.get("content", "")


def test_ingen_session_betyder_ingen_gaet(monkeypatch):
    """Har ejeren ingen session, oprettes ingen. Vi gaetter aldrig."""
    from core.services import routine_delivery as rd

    kaldt = []
    import core.services.session_inbox as si
    monkeypatch.setattr(si, "enqueue", lambda **kw: kaldt.append(kw))
    monkeypatch.setattr(
        "core.services.chat_sessions.most_recent_session_id_for_user",
        lambda uid: "",
    )
    monkeypatch.setattr(
        rd.db_routines, "get_run",
        lambda run_id, decrypt_for=None: {
            "run_id": run_id, "routine_id": "r1", "result": b"noget",
        },
    )
    monkeypatch.setattr(
        rd.db_routines, "get_routine",
        lambda rid, decrypt_for=None: {
            "name": "R", "access_scope": "user_private",
            "delivery_policy": {}, "workspace_name": None,
        },
    )

    rd._deliver_to_session(rd.DeliveryClaim(
        delivery_id="d2", run_id="run-2", owner_user_id="nobody",
        channel="desk", status="delivering", retry_count=0, lease_generation=1,
    ))
    assert kaldt == []


def test_systemrutiner_vaekker_ikke_en_session(monkeypatch):
    """Heartbeat/dream er rammer, ikke opgaver — de skal ikke skrive i en chat."""
    from core.services import routine_delivery as rd

    kaldt = []
    import core.services.session_inbox as si
    monkeypatch.setattr(si, "enqueue", lambda **kw: kaldt.append(kw))
    monkeypatch.setattr(
        "core.services.chat_sessions.most_recent_session_id_for_user",
        lambda uid: "chat-1",
    )
    monkeypatch.setattr(
        rd.db_routines, "get_run",
        lambda run_id, decrypt_for=None: {
            "run_id": run_id, "routine_id": "r1", "result": b"x",
        },
    )
    monkeypatch.setattr(
        rd.db_routines, "get_routine",
        lambda rid, decrypt_for=None: {
            "name": "heartbeat", "access_scope": "system_owner",
            "delivery_policy": {}, "workspace_name": None,
        },
    )

    rd._deliver_to_session(rd.DeliveryClaim(
        delivery_id="d3", run_id="run-3", owner_user_id="bjorn",
        channel="desk", status="delivering", retry_count=0, lease_generation=1,
    ))
    assert kaldt == []
