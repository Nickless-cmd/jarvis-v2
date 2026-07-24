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
