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
    s.clear_cache()
    monkeypatch.setattr(nk, "has_runtime_owner_key", lambda p: p == "xkiro")
    monkeypatch.setattr(s, "_profiles_root", lambda: Path("/findes-ikke"))
    assert s.ready_profiles_for("xkiro") == ["default"]


def test_udbyder_uden_runtime_noegle_forbliver_tom(monkeypatch):
    import core.services.auth_profile_scan as s
    import core.services.cheap_provider_runtime_keys as nk
    s.clear_cache()
    monkeypatch.setattr(nk, "has_runtime_owner_key", lambda p: False)
    monkeypatch.setattr(s, "_profiles_root", lambda: Path("/findes-ikke"))
    assert s.ready_profiles_for("noget-ukendt") == []


def test_rigtige_profiler_overlever_runtime_noeglen(monkeypatch):
    """Kortslutning her ville have fjernet HuggingFaces `account2`."""
    import core.services.auth_profile_scan as s
    import core.services.cheap_provider_runtime_keys as nk
    s.clear_cache()
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


def test_exception_frigor_laasen_og_rammer_kun_sin_slot(tmp_path, monkeypatch):
    """En exception under refresh må hverken efterlade låsen blokeret eller
    blinde hele auth-laget.

    24/10-2026: batch-scanningen fanger per slot. Før propagererede fejlen, men
    med ÉT fælles scan ville ét korrupt ``credentials.json`` ellers give nul
    profiler for ALLE providers — en værre fejl end den den rapporterede.
    Kontrakten er derfor: den defekte slot udelades, de øvrige svarer, og låsen
    frigives.
    """
    import threading
    from core.services import auth_profile_scan as s

    for p in ("groq", "cerebras"):
        (tmp_path / "default" / "providers" / p).mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    def delvist_boom(*, provider, auth_profile):
        if provider == "groq":
            raise RuntimeError("scan fejlede")
        return True

    monkeypatch.setattr(s, "provider_auth_ready", delvist_boom)

    # Den defekte slot udelades — den raske virker stadig i SAMME scan.
    assert s.ready_profiles_for("groq") == []
    assert s.ready_profiles_for("cerebras") == ["default"]

    # Leder-flaget blev nulstillet i `finally` (ellers ville næste scan hænge).
    assert s._SCAN_ACTIVE is False, "scan-flaget blev ikke nulstillet"
    assert s.auth_snapshot() is not None

    # Og et nyt scan (efter TTL/invalidering) heler den defekte slot.
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()

    svar: dict[str, list[str]] = {}
    faerdig = threading.Event()

    def andet_kald():
        svar["v"] = s.ready_profiles_for("groq")
        faerdig.set()

    t = threading.Thread(target=andet_kald, daemon=True)
    t.start()
    assert faerdig.wait(timeout=5), "låsen blev ikke frigivet efter exception"
    assert svar["v"] == ["default"]


def test_et_batch_scan_daekker_alle_providers(tmp_path, monkeypatch):
    """24/10-2026: låsen flyttede fra per-provider til ÉT batch-snapshot.

    Den erstatter den tidligere ``test_to_providers_refreshes_uafhaengigt``, som
    bevogtede det modsatte krav (at to providers kunne scannes uafhængigt).
    Målingen gjorde det krav forkert: 39 ``iterdir()``-kald for den SAMME mappe
    og 30 readiness-kald per kandidat-bygning, 264,89 ms koldt. Bygerne blev ikke
    færre af per-provider-låsen, fordi de samtidige tråde ramte HVER SIN provider
    og derfor aldrig mødtes om den samme lås.

    Ny kontrakt: ét scan besvarer alle providers. Prisen er serialisering — men
    den betales én gang per 60 s for hele processen, ikke én gang per provider.
    """
    from core.services import auth_profile_scan as s

    for p in ("groq", "cerebras", "mistral"):
        (tmp_path / "default" / "providers" / p).mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()

    assert s.ready_profiles_for("groq") == ["default"]
    assert s.ready_profiles_for("cerebras") == ["default"]
    assert s.ready_profiles_for("mistral") == ["default"]


def test_iterdir_kaldes_en_gang_for_alle_providers(tmp_path, monkeypatch):
    """``root.iterdir()`` skal kaldes ÉN gang, ikke én gang per provider.

    Målt før fixet: 39 kald for den samme mappe i ét enkelt
    ``_configured_cheap_candidates()``. Efter fixet: 1 (roden) + 1 per
    konto-profil (dens ``providers/``-mappe).
    """
    from pathlib import Path as _P
    from core.services import auth_profile_scan as s

    providere = ("groq", "cerebras", "mistral", "deepseek", "opencode")
    for prof in ("default", "account2"):
        for p in providere:
            (tmp_path / prof / "providers" / p).mkdir(parents=True)

    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()

    kald = {"n": 0}
    aegte = _P.iterdir

    def talt(self, *a, **k):
        if str(self).startswith(str(tmp_path)):
            kald["n"] += 1
        return aegte(self, *a, **k)

    monkeypatch.setattr(_P, "iterdir", talt)
    for p in providere:
        s.ready_profiles_for(p)

    # 1 = profiles-roden, 2 = providers/-mappen i hver konto-profil.
    # FØR fixet: 1 + 5 providere × 2 profiler = 11 (og 39 i produktion).
    assert kald["n"] <= 3, f"iterdir kaldt {kald['n']} gange — batch-scan mangler"


def test_samtidige_provider_kald_giver_et_batch_scan(tmp_path, monkeypatch):
    """N tråde om HVER SIN provider må ikke give N scans.

    Det var præcis fejlen per-provider-låsen ikke kunne se: trådene ramte
    forskellige providere, så de mødtes aldrig om samme lås og scannede alle.
    """
    import threading
    from pathlib import Path as _P
    from core.services import auth_profile_scan as s

    providere = ("groq", "cerebras", "mistral", "deepseek", "opencode", "groq")
    for p in set(providere):
        (tmp_path / "default" / "providers" / p).mkdir(parents=True)

    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    gate = threading.Event()
    foerste = {"sat": False}
    laas = threading.Lock()

    def langsom(*, provider, auth_profile):
        with laas:
            if not foerste["sat"]:
                foerste["sat"] = True
                holde = True
            else:
                holde = False
        if holde:
            gate.wait(timeout=5)   # hold batch-scanningen åben
        return True

    monkeypatch.setattr(s, "provider_auth_ready", langsom)

    kald = {"n": 0}
    aegte = _P.iterdir

    def talt(self, *a, **k):
        if str(self).startswith(str(tmp_path)):
            kald["n"] += 1
        return aegte(self, *a, **k)

    monkeypatch.setattr(_P, "iterdir", talt)

    # Deterministisk: `Barrier` sikrer at alle N kalder SAMTIDIG, og lederens
    # readiness holder scanningen ÅBEN indtil `release` — så de øvrige kan
    # hverken nå at se et hit eller selv blive ledere. Uden den holder havde
    # testen kun bevist at tråde der tilfældigvis overlappede delte et scan.
    start = threading.Barrier(len(providere))
    scan_aabnet = threading.Event()
    release = threading.Event()
    svar: list[list[str]] = []
    svar_laas = threading.Lock()

    def hold_scan_aaben(*, provider, auth_profile):
        scan_aabnet.set()
        assert release.wait(timeout=10), "release blev aldrig sat"
        return True

    monkeypatch.setattr(s, "provider_auth_ready", hold_scan_aaben)

    def arbejder(p):
        start.wait(timeout=5)
        r = s.ready_profiles_for(p)
        with svar_laas:
            svar.append(r)

    traade = [threading.Thread(target=arbejder, args=(p,)) for p in providere]
    for t in traade:
        t.start()
    assert scan_aabnet.wait(timeout=10), "ingen tråd startede scanningen"
    release.set()
    for t in traade:
        t.join(timeout=10)

    assert kald["n"] <= 2, f"iterdir kaldt {kald['n']} gange for 6 samtidige tråde"
    assert len(svar) == len(providere)
    assert all(r == ["default"] for r in svar)


def test_snapshot_returnerer_kopier(tmp_path, monkeypatch):
    """Kaldere må ikke dele mutérbare cache-objekter."""
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(s, "provider_auth_ready", lambda *, provider, auth_profile: True)
    s.clear_cache()

    foerste = s.auth_snapshot()
    foerste.setdefault("groq", []).append("injiceret")
    foerste["ny-provider"] = ["default"]

    anden = s.auth_snapshot()
    assert "injiceret" not in anden.get("groq", [])
    assert "ny-provider" not in anden

    # ready_profiles_for skal også give en frisk liste hver gang
    a = s.ready_profiles_for("groq")
    a.append("injiceret")
    assert s.ready_profiles_for("groq") == ["default"]


def test_save_og_revoke_invaliderer_snapshottet(tmp_path, monkeypatch):
    """En credential-ændring skal slå igennem straks, ikke efter 60 s TTL."""
    import core.auth.profiles as prof
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    monkeypatch.setattr(prof, "AUTH_PROFILES_DIR", tmp_path)

    klar = {"v": False}
    monkeypatch.setattr(
        s, "provider_auth_ready", lambda *, provider, auth_profile: klar["v"]
    )
    s.clear_cache()

    assert s.ready_profiles_for("groq") == []

    # Nøglen bliver gyldig på disken — men snapshottet holder i 60 s.
    klar["v"] = True
    assert s.ready_profiles_for("groq") == [], "cachen skal stadig holde her"

    prof.save_provider_credentials(
        profile="default", provider="groq", credentials={"api_key": "x"}  # pragma: allowlist secret
    )
    assert s.ready_profiles_for("groq") == ["default"], (
        "save_provider_credentials invaliderede ikke auth-snapshottet"
    )

    # ... og revoke skal gøre det modsatte med det samme.
    klar["v"] = False
    prof.revoke_provider(profile="default", provider="groq")
    assert s.ready_profiles_for("groq") == [], (
        "revoke_provider invaliderede ikke auth-snapshottet"
    )


def test_credential_gemning_under_aktivt_scan_laaser_ikke(tmp_path, monkeypatch):
    """Regression: en credential-skrivning inde i scanningen må ikke låse auth-laget.

    MÅLT 24/10-2026: `provider_auth_ready()` for `openai-codex` kalder
    `get_openai_bearer_token()` → `refresh_openai_access_token()` →
    `save_provider_credentials()` → `clear_cache()`. Den første udgave af
    batch-snapshottet holdt en almindelig `threading.Lock` gennem hele
    scanningen, så en vellykket token-refresh låste hele auth-laget permanent.
    Reproduceret: `deadlock_reproduceret = True`.

    Kontrakten: scanningen må ikke holde låsen under I/O, så en invalidering
    inde fra readiness-stien skal gå igennem — og scanningen må ikke publicere
    sit nu forældede resultat.
    """
    import threading
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    invalideret = threading.Event()

    def readiness_der_skriver(*, provider, auth_profile):
        # Præcis den sti der låste før: skrivning midt i scanningen.
        s.clear_cache()
        invalideret.set()
        return True

    monkeypatch.setattr(s, "provider_auth_ready", readiness_der_skriver)

    resultat: dict[str, dict[str, list[str]]] = {}
    traad = threading.Thread(
        target=lambda: resultat.setdefault("snap", s.auth_snapshot()), daemon=True
    )
    traad.start()
    traad.join(timeout=5)

    assert not traad.is_alive(), "scanningen låste — clear_cache() må ikke tage scan-låsen"
    assert invalideret.is_set(), "readiness blev aldrig kørt"
    # Scanningen startede med generation G og blev invalideret undervejs, så
    # dens resultat blev KASSERET — ikke publiceret som friskt.
    assert s._SNAPSHOT is None, "et invalideret scan publicerede sit forældede resultat"


def test_invalidering_undervejs_kasserer_resultatet(tmp_path, monkeypatch):
    """Et scan der invalideres undervejs må ikke overskrive det friske billede."""
    from core.services import auth_profile_scan as s

    (tmp_path / "default" / "providers" / "groq").mkdir(parents=True)
    monkeypatch.setattr(s, "_profiles_root", lambda: tmp_path)
    s.clear_cache()

    kald = {"n": 0}

    def readiness(*, provider, auth_profile):
        kald["n"] += 1
        if kald["n"] == 1:
            s.clear_cache()  # invaliderer FØRSTE scan
            return True
        return False  # anden scan: ikke klar

    monkeypatch.setattr(s, "provider_auth_ready", readiness)

    # Kaldet får sit eget scan-svar (det var sandt da det blev målt), men det
    # må IKKE lægges i cachen — næste kald skal se den nye sandhed.
    s.auth_snapshot()
    assert s._SNAPSHOT is None, (
        "det invaliderede scan publicerede alligevel — generationstjekket virker ikke"
    )
    # Næste kald scanner igen og ser den NYE sandhed (ikke klar).
    assert s.ready_profiles_for("groq") == []
