import sqlite3
from unittest import mock

import pytest

from core.services import central_keymaker as km


@pytest.fixture
def tmpdb(tmp_path):
    """Peg keymaker's connect() på en midlertidig fil-DB (persisterer mellem kald i testen)."""
    path = str(tmp_path / "km.db")

    def _connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    with mock.patch("core.services.central_keymaker.connect", side_effect=_connect):
        yield


def test_earns_key_only_at_volume_and_zero_nongreen(tmpdb):
    fake = {
        "veto": {"cluster": "commit", "total": 124, "green": 124},          # ≥100, 0 fejl → OPTJENER
        "decision_gate": {"cluster": "commit", "total": 40, "green": 40},    # <100 → for lidt volumen
        "memory_promotion": {"cluster": "memory", "total": 500, "green": 90},  # fejl → nej
    }
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        out = km.evaluate_keys()
    domains = {e["domain"] for e in out["earned"]}
    assert domains == {"decentralize:veto"}
    issued = {e["domain"] for e in out["issued"]}
    assert issued == {"decentralize:veto"}


def test_security_gate_never_earns_key(tmpdb):
    fake = {"cross_user_share": {"cluster": "privacy", "total": 5000, "green": 5000}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        out = km.evaluate_keys()
    assert out["earned"] == [] and out["issued"] == []


def test_catalog_security_nerve_outside_denylist_never_earns(tmpdb):
    """§11.3-hullet Rådet fandt: outbound_scrub er katalog-SECURITY men IKKE i _NEVER-frozensettet.
    Klasse-baseret _is_never() skal blokere den alligevel — ellers kan et altid-grønt sikkerheds-
    instrument optjene en decentraliserings-nøgle."""
    assert "outbound_scrub" not in km._NEVER          # bekræft at fallback-listen IKKE dækker den
    fake = {"outbound_scrub": {"cluster": "privacy", "total": 5000, "green": 5000}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        out = km.evaluate_keys()
    assert out["earned"] == [] and out["issued"] == []


def test_approve_rejects_security_key_defense_in_depth(tmpdb):
    """Selv hvis en SECURITY-nøgle bliver INSERTet direkte (race/drift), må approve_key ALDRIG
    flippe flaget — den skal afvise + markere 'rejected'."""
    flips = []
    with mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled",
                       side_effect=lambda s, n, e: flips.append((s, n, e))):
        conn = km.connect()
        km._ensure_table(conn)
        conn.execute(
            """INSERT INTO central_keys (domain, unlock_scope, unlock_name, track_value,
               issued_at, status, reason) VALUES (?,?,?,?,?,'pending',?)""",
            ("decentralize:abuse_monitor", "decentralize", "abuse_monitor", 9999,
             km._now().isoformat(), "manuelt indsat"))
        conn.commit()
        key_id = conn.execute("SELECT id FROM central_keys").fetchone()[0]
        conn.close()
        res = km.approve_key(key_id)
    assert res["ok"] is False
    assert flips == []                                # flaget blev ALDRIG flippet
    row = [k for k in km.list_keys(include_expired=True) if k["id"] == key_id][0]
    assert row["status"] == "rejected"


def test_no_duplicate_pending_key(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"):
        km.evaluate_keys()
        second = km.evaluate_keys()
    assert second["issued"] == []            # allerede pending → udsteder ikke igen
    assert [e["domain"] for e in second["earned"]] == ["decentralize:veto"]
    assert len([k for k in km.list_keys() if k["domain"] == "decentralize:veto"]) == 1


def test_approve_flips_flag_and_sets_ttl(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    flips = []
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled",
                       side_effect=lambda s, n, e: flips.append((s, n, e))):
        km.evaluate_keys()
        key_id = km.list_keys()[0]["id"]
        res = km.approve_key(key_id)
    assert res["ok"] and res["domain"] == "decentralize:veto"
    assert flips == [("decentralize", "veto", True)]
    row = [k for k in km.list_keys() if k["id"] == key_id][0]
    assert row["status"] == "approved" and row["expires_at"]


def test_approve_unknown_id_is_safe(tmpdb):
    with mock.patch("core.services.central_keymaker._observe"):
        res = km.approve_key(9999)
    assert res["ok"] is False


def test_expire_due_reverts_flag(tmpdb):
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    flips = []
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled",
                       side_effect=lambda s, n, e: flips.append((s, n, e))):
        km.evaluate_keys()
        key_id = km.list_keys()[0]["id"]
        km.approve_key(key_id)
        # tving udløb i fortiden
        import sqlite3 as _s
        conn = km.connect()
        conn.execute("UPDATE central_keys SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                     (key_id,))
        conn.commit()
        conn.close()
        out = km.expire_due()
    assert out["expired"] == 1
    assert ("decentralize", "veto", False) in flips
    row = [k for k in km.list_keys(include_expired=True) if k["id"] == key_id][0]
    assert row["status"] == "expired"


def test_is_decentralized_requires_valid_approved_key(tmpdb):
    """Konsum-check: kun en ÆGTE approved+ikke-udløbet nøgle tæller — ikke pending, ikke udløbet,
    ikke fravær. (Modellen bygger på at is_enabled-default IKKE bruges som konsum-gate.)"""
    fake = {"veto": {"cluster": "commit", "total": 124, "green": 124}}
    assert km.is_decentralized("veto") is False          # ingen nøgle → False
    with mock.patch("core.services.gate_verdict_ledger.summary", return_value=fake), \
            mock.patch("core.services.central_keymaker._observe"), \
            mock.patch("core.services.central_switches.set_enabled"):
        km.evaluate_keys()
        assert km.is_decentralized("veto") is False      # pending → False
        key_id = km.list_keys()[0]["id"]
        km.approve_key(key_id)
        assert km.is_decentralized("veto") is True        # approved + fremtidig TTL → True
        conn = km.connect()
        conn.execute("UPDATE central_keys SET expires_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                     (key_id,))
        conn.commit()
        conn.close()
        assert km.is_decentralized("veto") is False       # udløbet → False
    assert km.is_decentralized("decision_gate") is False   # anden nerve → aldrig


# ---------------------------------------------------------------------------
# Varsling (7/9-2026)
#
# Maskineriet virkede hele vejen — optjening, tærskel, TTL — men det sidste led
# var at nogen tilfældigvis kiggede i en tabel. Tre nøgler lå PENDING i to
# måneder (veto med 1.193 beslutninger fra 10. juli), og en fjerde blev udstedt
# 6. juli og **udløb ubemærket** 10. juli. En nøgle der udløber uden godkendelse
# er tabt arbejde.
# ---------------------------------------------------------------------------

def test_en_ny_noegle_varsler_ejeren(monkeypatch):
    import core.services.central_keymaker as K

    sendt: list = []
    monkeypatch.setattr(K, "_ejer_uid", lambda: "u1")
    monkeypatch.setattr("core.services.notification_router.route_proactive_notification",
                        lambda uid, t, p, importance="normal": sendt.append((t, p)) or {"delivered": True})

    assert K._varsl_ejer("decentralize:veto", 1193) is True
    ntype, payload = sendt[0]
    assert ntype == "keymaker_key_earned"
    assert "veto" in payload["message"] and "1193" in payload["message"]


def test_beskeden_baerer_kommandoen_fordi_verbet_er_svaert_at_gaette(monkeypatch):
    """Det hedder `unlock`, ikke `approve` — `approve` er bundet til
    tool-intents, autonomi-forslag og initiativer og rammer ikke nøgler."""
    import core.services.central_keymaker as K

    sendt: list = []
    monkeypatch.setattr(K, "_ejer_uid", lambda: "u1")
    monkeypatch.setattr("core.services.notification_router.route_proactive_notification",
                        lambda uid, t, p, importance="normal": sendt.append(p) or {"delivered": True})
    K._varsl_ejer("decentralize:veto", 1193)
    assert "unlock" in sendt[0]["message"]


def test_uden_ejer_sendes_der_intet(monkeypatch):
    import core.services.central_keymaker as K

    monkeypatch.setattr(K, "_ejer_uid", lambda: "")
    with monkeypatch.context() as m:
        kaldt: list = []
        m.setattr("core.services.notification_router.route_proactive_notification",
                  lambda *a, **kw: kaldt.append(1) or {"delivered": True})
        assert K._varsl_ejer("decentralize:veto", 10) is False
        assert kaldt == []


def test_en_fejlet_varsling_forhindrer_ikke_at_noeglen_udstedes(monkeypatch):
    """Notifikationen er en bekvemmelighed; nøglen er arbejdet."""
    import core.services.central_keymaker as K

    def eksploder(*a, **kw):
        raise RuntimeError("ntfy nede")

    monkeypatch.setattr(K, "_ejer_uid", lambda: "u1")
    monkeypatch.setattr("core.services.notification_router.route_proactive_notification", eksploder)
    assert K._varsl_ejer("decentralize:veto", 10) is False


# ── påmindelsen ──────────────────────────────────────────────────────────────

def test_paamindelsen_er_rate_limiteret_til_en_gang_i_doegnet(monkeypatch):
    import core.services.central_keymaker as K

    monkeypatch.setattr("core.services.shared_cache.get", lambda k: True)
    assert K._mind_om_ventende() == 0


def test_uden_rate_limit_minder_vi_hellere_ikke(monkeypatch):
    """Kan cachen ikke nås, kan vi ikke garantere én om dagen — og en
    påmindelse pr. cadence-tick ville lære ham at ignorere kanalen."""
    import core.services.central_keymaker as K

    def eksploder(*a, **kw):
        raise RuntimeError("cache væk")

    monkeypatch.setattr("core.services.shared_cache.get", eksploder)
    assert K._mind_om_ventende() == 0


def test_expire_due_kalder_paamindelsen(monkeypatch):
    """Uden koblingen ville modulet være endnu et der er bygget og ikke kaldt."""
    import inspect

    import core.services.central_keymaker as K

    assert "_mind_om_ventende" in inspect.getsource(K.expire_due)
