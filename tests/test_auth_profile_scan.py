from pathlib import Path

def test_ready_profiles_for_scans_dirs(tmp_path, monkeypatch):
    from core.services import auth_profile_scan as s
    # build auth/profiles/{default,account2}/providers/groq/
    for prof in ("default", "account2"):
        (tmp_path / prof / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()
    assert s.ready_profiles_for("groq") == ["default", "account2"]  # default first


def test_skips_unready_profiles(tmp_path, monkeypatch):
    from core.services import auth_profile_scan as s
    for prof in ("default", "account2"):
        (tmp_path / prof / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready",
                        lambda *, provider, auth_profile: auth_profile == "default")
    s.clear_cache()
    assert s.ready_profiles_for("groq") == ["default"]


def test_keyless_is_single_profile(tmp_path, monkeypatch):
    from core.services import auth_profile_scan as s
    for prof in ("default", "account2"):
        (tmp_path / prof / "providers" / "ollamafreeapi").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()
    assert s.ready_profiles_for("ollamafreeapi") == ["default"]


def test_bearer_public_proxy_rotates_account2(tmp_path, monkeypatch):
    # opencode is in _PUBLIC_PROXIES but auth_kind=bearer (real per-account keys) —
    # it must NOT be treated keyless, so its account2 key is surfaced for rotation.
    from core.services import auth_profile_scan as s
    for prof in ("default", "account2"):
        (tmp_path / prof / "providers" / "opencode").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()
    assert s._is_keyless("opencode") is False
    assert s.ready_profiles_for("opencode") == ["default", "account2"]


def test_only_account_profiles_not_backups_or_legacy(tmp_path, monkeypatch):
    # Regression: the live flip revealed default.bak-* + single-provider/OAuth profile
    # dirs were wrongly materialized as account slots. Only default + account<N> count.
    from core.services import auth_profile_scan as s
    for prof in ("default", "account2", "account3",
                 "default.bak-20260716-150508",  # backup -> excluded
                 "groq", "mistral", "gemini",     # single-provider legacy -> excluded
                 "codex", "copilot"):             # OAuth -> excluded
        (tmp_path / prof / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()
    assert s.ready_profiles_for("groq") == ["default", "account2", "account3"]


def test_cache_ttl_avoids_rescan(tmp_path, monkeypatch):
    from core.services import auth_profile_scan as s
    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    calls = {"n": 0}
    def counting(*, provider, auth_profile): calls["n"] += 1; return True
    monkeypatch.setattr(s, "provider_auth_ready", counting)
    s.clear_cache()
    s.ready_profiles_for("groq"); s.ready_profiles_for("groq")
    assert calls["n"] == 1   # second call served from cache


# ── Delt ejer-nøgle i runtime.json (7/9-2026) ────────────────────────────────
# xkiro var klar og svarede på direkte kald, men kom aldrig i cheap-puljen:
# profil-listen var tom, fordi nøglen ikke ligger i et profil-arkiv.

def test_runtime_noegle_giver_default_profil(monkeypatch):
    import core.services.auth_profile_scan as s
    import core.services.cheap_provider_runtime_keys as nk
    s._CACHE.clear()
    monkeypatch.setattr(nk, "has_runtime_owner_key", lambda p: p == "xkiro")
    monkeypatch.setattr(s, "_profiles_root", lambda: Path("/findes-ikke"))
    assert s.ready_profiles_for("xkiro") == ["default"]


def test_udbyder_uden_runtime_noegle_forbliver_tom(monkeypatch):
    import core.services.auth_profile_scan as s
    import core.services.cheap_provider_runtime_keys as nk
    s._CACHE.clear()
    monkeypatch.setattr(nk, "has_runtime_owner_key", lambda p: False)
    monkeypatch.setattr(s, "_profiles_root", lambda: Path("/findes-ikke"))
    assert s.ready_profiles_for("noget-ukendt") == []


def test_rigtige_profiler_overlever_runtime_noeglen(monkeypatch):
    """Kortslutning her ville have fjernet HuggingFaces `account2`."""
    import core.services.auth_profile_scan as s
    import core.services.cheap_provider_runtime_keys as nk
    s._CACHE.clear()
    monkeypatch.setattr(nk, "has_runtime_owner_key", lambda p: True)
    monkeypatch.setattr(s, "ready_profiles_for", s.ready_profiles_for)
    kaldt = {}

    def falsk_root():
        kaldt["scannet"] = True
        return Path("/findes-ikke")

    monkeypatch.setattr(s, "_profiles_root", falsk_root)
    ud = s.ready_profiles_for("huggingface")
    assert kaldt.get("scannet"), "scanningen skal stadig køre — ikke kortsluttes"
    assert "default" in ud


# ── Single-flight (24/10-2026) ───────────────────────────────────────────────
# MÅLT: `ready_profiles_for` havde en 60s-cache UDEN lås. Fem samtidige
# cognitive-state-tråde kunne alle se samme udløb og køre den samme 235 ms
# directory-scan. Bygerne kom med 70/68/124 sekunders mellemrum — cache-expiry.
# Den eksisterende test_cache_ttl_avoids_rescan er enkelttrådet og kan ikke se
# stampeden. Disse er dens flertrådede tvillinger.

def test_single_flight_kun_et_scan(tmp_path, monkeypatch):
    """N tråde mod samme kolde provider skal give PRÆCIS ÉT scan.

    Determinisme: den første tråd der når provider_auth_ready holder sin scan
    åben på en Event indtil de øvrige har haft tid til at ramme låsen. Uden lås
    kalder alle N provider_auth_ready (tælleren bliver N) — med lås venter de
    øvrige og får cache-hit (tælleren bliver 1). Retningen er derfor sikker
    uanset scheduling: på den nuværende kode kan de ikke undgå at tælle med.
    """
    import threading
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    calls = {"n": 0}
    taeller_laas = threading.Lock()
    gate = threading.Event()
    start = threading.Barrier(8)

    def langsom(*, provider, auth_profile):
        with taeller_laas:
            calls["n"] += 1
            foerst = calls["n"] == 1
        if foerst:
            gate.wait(timeout=5)   # hold vinderens scan åben
        return True

    monkeypatch.setattr(s, "provider_auth_ready", langsom)

    resultater: list[list[str]] = []
    res_laas = threading.Lock()

    def arbejder():
        start.wait(timeout=5)
        r = s.ready_profiles_for("groq")
        with res_laas:
            resultater.append(r)

    traade = [threading.Thread(target=arbejder) for _ in range(8)]
    for t in traade:
        t.start()
    gate.set()
    for t in traade:
        t.join(timeout=10)

    assert calls["n"] == 1, f"scannede {calls['n']} gange — single-flight mangler"
    assert len(resultater) == 8
    assert all(r == ["default"] for r in resultater)


def test_exception_frigor_laasen(tmp_path, monkeypatch):
    """En exception under refresh må ikke efterlade låsen blokeret."""
    import threading
    import pytest
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    def boom(*, provider, auth_profile):
        raise RuntimeError("scan fejlede")

    monkeypatch.setattr(s, "provider_auth_ready", boom)
    with pytest.raises(RuntimeError):
        s.ready_profiles_for("groq")

    monkeypatch.setattr(s, "provider_auth_ready",
                        lambda *, provider, auth_profile: True)

    svar: dict[str, list[str]] = {}
    faerdig = threading.Event()

    def andet_kald():
        svar["v"] = s.ready_profiles_for("groq")
        faerdig.set()

    t = threading.Thread(target=andet_kald, daemon=True)
    t.start()
    assert faerdig.wait(timeout=5), "låsen blev ikke frigivet efter exception"
    assert svar["v"] == ["default"]


def test_to_providers_refreshes_uafhaengigt(tmp_path, monkeypatch):
    """En global refresh-lås ville serialisere forskellige providers.

    groq holder sin scan åben; cerebras skal kunne fuldføre imens. Er låsen
    global, venter cerebras til groq's timeout — det måles på væguret.
    """
    import threading
    import time
    from core.services import auth_profile_scan as s

    for p in ("groq", "cerebras"):
        (tmp_path / "default" / "providers" / p).mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    groq_inde = threading.Event()
    cerebras_faerdig = threading.Event()

    def ready(*, provider, auth_profile):
        if provider == "groq":
            groq_inde.set()
            cerebras_faerdig.wait(timeout=5)   # lang nok til at måle blokering
        elif provider == "cerebras":
            cerebras_faerdig.set()
        return True

    monkeypatch.setattr(s, "provider_auth_ready", ready)

    t = threading.Thread(target=lambda: s.ready_profiles_for("groq"), daemon=True)
    t.start()
    assert groq_inde.wait(timeout=5), "groq-scan startede ikke"

    t0 = time.monotonic()
    s.ready_profiles_for("cerebras")
    ventet = time.monotonic() - t0

    assert ventet < 1.0, (
        f"cerebras ventede {ventet:.1f}s bag groq — låsen er global, ikke per-provider"
    )
    t.join(timeout=10)
    assert not t.is_alive()
