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
