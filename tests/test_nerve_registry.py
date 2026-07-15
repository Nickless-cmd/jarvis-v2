"""Tests for den selv-registrerende nerve-arkitektur (spec 2026-07-13, Fase B + C).

Dækker:
  * Fase B: durabel registrerings-round-trip, 3 kontrakt-varianter validerer, to_manifest,
    rolle-baseret strenghed, capability-kohærens, selv-sikkerhed.
  * Fase C: usigneret/uverificeret plugin bliver ALDRIG aktiveret (stays pending/rejected);
    et signeret + godkendt plugin KAN aktiveres. Sandbox/isolation: kastende loader → suspended.

Kører uden ægte DB: runtime_state monkeypatches til en in-memory dict (samme mønster som
tests/test_promise_ledger.py). Identitets-hemmeligheder monkeypatches ind, så vi aldrig rører
en rigtig runtime.json.
"""
from __future__ import annotations

import hashlib
import hmac

import pytest

import core.services.nerve_registry as nr


# ── In-memory runtime_state (ingen DB i unit-test) ──────────────────────────
@pytest.fixture()
def mem_store(monkeypatch):
    store: dict = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))

    def _set(k, v, **kw):
        store[k] = v

    monkeypatch.setattr(dbc, "set_runtime_state_value", _set)
    return store


# ── Injicér identitets-hemmeligheder (aldrig en rigtig runtime.json) ────────
_SECRETS = {"owner": b"owner-secret-xyz", "claude": b"claude-secret-abc",
            "jarvis": b"jarvis-secret-123"}


@pytest.fixture()
def signed(monkeypatch):
    monkeypatch.setattr(nr, "_identity_secret",
                        lambda tier: _SECRETS.get(str(tier).strip().lower()))

    def _sign(manifest, tier=None):
        t = str(tier or manifest.identity_tier or "").strip().lower()
        secret = _SECRETS.get(t)
        if not secret:
            return ""
        return hmac.new(secret, nr._canonical_identity_payload(manifest),
                        hashlib.sha256).hexdigest()

    return _sign


# ── Manifest-fabrik ──────────────────────────────────────────────────────────
def _nerve_manifest(**over):
    base = dict(
        name="test_nerve", cluster="central_meta", kind="probe",
        contract_variant=nr.ContractVariant.NERVE.value,
        kill_switch_key="flag:central.switch.central_meta.test_nerve",
        klass="cognitive", identity_tier=nr.IdentityTier.OWNER.value,
        capabilities=[nr.Capability.OBSERVE_ONLY.value],
        mode=nr.Mode.SHADOW.value, module_path="core.services.foo", entrypoint="run",
        interface={"input_ctx": ["x"], "output": "Signal"},
    )
    base.update(over)
    return nr.NerveManifest(**base)


# ═══════════════════════════ Fase B — kontrakt ═══════════════════════════════
def test_compliant_manifest_validates_clean():
    assert nr.validate_manifest(_nerve_manifest()) == []
    assert nr.is_compliant(_nerve_manifest())


def test_missing_kill_switch_rejected_with_precise_error():
    errs = nr.validate_manifest(_nerve_manifest(kill_switch_key=""))
    assert any("kill_switch_key" in e for e in errs)


def test_three_contract_variants_validate():
    """De TRE kontrakt-varianter (gate_cluster / daemon_cluster / nerve) validerer hver."""
    nerve = _nerve_manifest(contract_variant=nr.ContractVariant.NERVE.value,
                            interface={"input_ctx": [], "output": "Signal"})
    gate = _nerve_manifest(name="g", contract_variant=nr.ContractVariant.GATE_CLUSTER.value,
                           kill_switch_key="k", interface={"input_ctx": [], "output": "Verdict"})
    daemon = _nerve_manifest(name="d", contract_variant=nr.ContractVariant.DAEMON_CLUSTER.value,
                             kill_switch_key="k", interface={"tick": "5s"})
    assert nr.validate_manifest(nerve) == []
    assert nr.validate_manifest(gate) == []
    assert nr.validate_manifest(daemon) == []


def test_variant_specific_interface_required():
    # gate-variant uden 'output' → afvist; daemon-variant uden 'tick' → afvist
    gate = _nerve_manifest(contract_variant=nr.ContractVariant.GATE_CLUSTER.value, interface={})
    daemon = _nerve_manifest(contract_variant=nr.ContractVariant.DAEMON_CLUSTER.value, interface={})
    assert any("output" in e for e in nr.validate_manifest(gate))
    assert any("tick" in e for e in nr.validate_manifest(daemon))


def test_capability_coherence_enforced():
    m = _nerve_manifest(capabilities=[nr.Capability.OBSERVE_ONLY.value,
                                      nr.Capability.CAN_BLOCK.value])
    assert any("observe_only" in e for e in nr.validate_manifest(m))


def test_unknown_identity_tier_rejected():
    m = _nerve_manifest(identity_tier="stranger")
    assert any("identitets-tier" in e for e in nr.validate_manifest(m))


def test_invariants_must_be_on():
    for fld in ("trace", "log", "learning", "central_authority"):
        m = _nerve_manifest(**{fld: False})
        assert nr.validate_manifest(m), f"{fld}=False burde afvises"


def test_jarvis_hand_capability_cannot_start_on():
    """Rolle-strenghed: jarvis + en hånd (can_block) + mode 'on' = kontrakt-brud."""
    m = _nerve_manifest(identity_tier=nr.IdentityTier.JARVIS.value,
                        capabilities=[nr.Capability.CAN_BLOCK.value], mode=nr.Mode.ON.value)
    assert any("kræver approval" in e for e in nr.validate_manifest(m))
    # observe_only i shadow er derimod fint for jarvis
    ok = _nerve_manifest(identity_tier=nr.IdentityTier.JARVIS.value,
                         capabilities=[nr.Capability.OBSERVE_ONLY.value], mode=nr.Mode.SHADOW.value)
    assert nr.validate_manifest(ok) == []


def test_register_roundtrips_durably(mem_store):
    res = nr.register(_nerve_manifest(name="round_trip"))
    assert res["ok"] and res["errors"] == []
    # Durabelt: en frisk læsning (samme KV-store) ser manifestet
    assert nr.is_registered("round_trip")
    got = nr.get_manifest("round_trip")
    assert got is not None and got.name == "round_trip"
    assert got.cluster == "central_meta"
    assert "round_trip" in nr.registered_names()
    assert "round_trip" in nr.compliant_names()
    # Faktisk landede i den durable KV under den forventede nøgle
    assert "round_trip" in mem_store.get(nr._MANIFEST_KEY, {})


def test_register_rejects_noncompliant(mem_store):
    res = nr.register(_nerve_manifest(name="bad", kill_switch_key=""))
    assert not res["ok"]
    assert not nr.is_registered("bad")


def test_to_manifest_adapter_from_dict_and_object(mem_store):
    # dict-descriptor
    m1 = nr.to_manifest({"cluster": "auth", "nerve": "oauth_state"},
                        contract_variant=nr.ContractVariant.NERVE.value, kind="auth",
                        klass="security")
    assert m1.name == "oauth_state" and m1.cluster == "auth"
    # kill_switch_key udledes automatisk fra cluster/name
    assert m1.kill_switch_key.endswith("auth.oauth_state")
    assert nr.is_compliant(m1)

    # objekt-descriptor
    class _Desc:
        cluster = "x"
        nerve = "y"

    m2 = nr.to_manifest(_Desc())
    assert m2.name == "y" and m2.cluster == "x"


def test_seed_known_nerves_registers_all(mem_store):
    results = nr.seed_known_nerves()
    assert all(r.get("ok") for r in results), results
    for name in ("gate_pattern_repeat", "oauth_state", "fact_gate"):
        assert nr.is_registered(name)


def test_registry_self_safe_on_kv_failure(monkeypatch):
    # Selv med en kastende KV-backend må intet boble op
    import core.runtime.db_core as dbc

    def _boom(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr(dbc, "get_runtime_state_value", _boom)
    monkeypatch.setattr(dbc, "set_runtime_state_value", _boom)
    assert nr.all_manifests() == []
    assert nr.registered_names() == set()
    res = nr.register(_nerve_manifest())
    assert not res["ok"]  # skrivning fejlede self-safe, ingen exception


# ═══════════════════════════ Fase C — governance ════════════════════════════
def test_unsigned_plugin_never_activates(mem_store, monkeypatch):
    """Et USIGNERET plugin → REJECTED ved submit, ALDRIG aktiverbart."""
    monkeypatch.setattr(nr, "_identity_secret",
                        lambda tier: _SECRETS.get(str(tier).strip().lower()))
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="unsigned", identity_signature="")  # ingen signatur
    sub = loader.submit(m)
    assert sub["status"] == nr.PluginStatus.REJECTED.value
    assert any("identitets-signatur" in e for e in sub["errors"])
    # Approval + activate må ikke kunne redde en afvist plugin
    assert loader.approve("unsigned", approver_tier="owner")["status"] == \
        nr.PluginStatus.REJECTED.value
    act = loader.activate("unsigned")
    assert act["status"] != nr.PluginStatus.ACTIVE.value
    assert not loader.is_active("unsigned")


def test_forged_signature_rejected(mem_store, monkeypatch):
    """En fremmed uden hemmeligheden kan ikke forfalske en gyldig signatur."""
    monkeypatch.setattr(nr, "_identity_secret",
                        lambda tier: _SECRETS.get(str(tier).strip().lower()))
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="forged", identity_signature="deadbeef" * 8)
    sub = loader.submit(m)
    assert sub["status"] == nr.PluginStatus.REJECTED.value
    assert not loader.is_active("forged")


def test_signed_plugin_pending_until_approved_then_active(mem_store, signed):
    """Signeret plugin → PENDING (aldrig auto-on) → efter approval → aktiverbar."""
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="good", identity_tier=nr.IdentityTier.OWNER.value)
    m.identity_signature = signed(m)
    # submit → PENDING, IKKE active
    sub = loader.submit(m)
    assert sub["status"] == nr.PluginStatus.PENDING.value
    assert not loader.is_active("good")
    # aktivering FØR approval afvises
    early = loader.activate("good")
    assert early["status"] != nr.PluginStatus.ACTIVE.value
    assert not loader.is_active("good")
    # approval af owner → APPROVED → activate → ACTIVE
    appr = loader.approve("good", approver_tier="owner")
    assert appr["status"] == nr.PluginStatus.APPROVED.value
    act = loader.activate("good")
    assert act["status"] == nr.PluginStatus.ACTIVE.value
    assert loader.is_active("good")
    # og manifestet er nu registreret i Fase-B-registry
    assert nr.is_registered("good")


def test_only_owner_or_claude_can_approve(mem_store, signed):
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="jmod", identity_tier=nr.IdentityTier.OWNER.value)
    m.identity_signature = signed(m)
    loader.submit(m)
    # jarvis kan ikke godkende
    bad = loader.approve("jmod", approver_tier="jarvis")
    assert bad["status"] is None and bad["errors"]
    assert not loader.is_active("jmod")
    # claude kan
    assert loader.approve("jmod", approver_tier="claude")["status"] == \
        nr.PluginStatus.APPROVED.value


def test_jarvis_plugin_requires_trusted_approval(mem_store, signed):
    """Jarvis-modul med en hånd: registreres PENDING, aktiveres kun efter owner/claude."""
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="jhand", identity_tier=nr.IdentityTier.JARVIS.value,
                        capabilities=[nr.Capability.CAN_EMIT.value], mode=nr.Mode.SHADOW.value)
    m.identity_signature = signed(m)
    sub = loader.submit(m)
    assert sub["status"] == nr.PluginStatus.PENDING.value  # aldrig auto-on
    loader.approve("jhand", approver_tier="owner")
    assert loader.activate("jhand")["status"] == nr.PluginStatus.ACTIVE.value


def test_activation_sandbox_suspends_on_crash(mem_store, signed):
    """Isolation (Fase C §4): en kastende loader_fn → SUSPENDED, ikke et crash."""
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="crasher", identity_tier=nr.IdentityTier.OWNER.value)
    m.identity_signature = signed(m)
    loader.submit(m)
    loader.approve("crasher", approver_tier="owner")

    def _boom(_manifest):
        raise RuntimeError("plugin eksploderede")

    act = loader.activate("crasher", loader_fn=_boom)
    assert act["status"] == nr.PluginStatus.SUSPENDED.value
    assert not loader.is_active("crasher")


def test_pending_queue_lists_only_pending(mem_store, signed):
    loader = nr.GovernedPluginLoader()
    m = _nerve_manifest(name="p1", identity_tier=nr.IdentityTier.OWNER.value)
    m.identity_signature = signed(m)
    loader.submit(m)
    names = [r["name"] for r in loader.pending()]
    assert "p1" in names


def test_sign_and_verify_roundtrip(mem_store, monkeypatch):
    """sign_manifest ↔ verify_identity round-trip mod injiceret hemmelighed."""
    monkeypatch.setattr(nr, "_identity_secret",
                        lambda tier: _SECRETS.get(str(tier).strip().lower()))
    m = _nerve_manifest(name="rt", identity_tier=nr.IdentityTier.CLAUDE.value)
    m.identity_signature = nr.sign_manifest(m)
    assert m.identity_signature
    assert nr.verify_identity(m)
    # Manipulér et signeret felt → signaturen holder ikke længere
    m.module_path = "core.services.evil"
    assert not nr.verify_identity(m)


def test_verify_fails_closed_without_secret(monkeypatch):
    """Mangler hemmeligheden på maskinen → verifikation fejler-lukket (afvist)."""
    monkeypatch.setattr(nr, "_identity_secret", lambda tier: None)
    m = _nerve_manifest(identity_tier=nr.IdentityTier.OWNER.value,
                        identity_signature="abc")
    assert not nr.verify_identity(m)
