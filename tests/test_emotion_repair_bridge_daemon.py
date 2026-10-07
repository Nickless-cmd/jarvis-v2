from core.services import emotion_repair_bridge_daemon as erbd


def test_build_emotion_repair_bridge_surface_is_read_only_projection():
    surface = erbd.build_emotion_repair_bridge_surface()

    assert surface["mode"] == "emotion-repair-bridge-daemon"
    assert surface["authority"] == "db-derived-read-only"
    assert "summary" in surface
    assert "patterns" in surface
    assert "recent_attempts" in surface


def test_emotion_repair_bridge_surface_registered_in_signal_router():
    from core.services.signal_surface_router import get_surface_names, read_surface

    assert "emotion_repair_bridge" in get_surface_names()
    surface = read_surface("emotion_repair_bridge")
    assert surface["mode"] == "emotion-repair-bridge-daemon"


# ── Hanen: hvornår er en selvreparation en sansning? (28/9-2026) ────────
# Baggrund: broen skrev HVER reparation til Sansernes Arkiv, begge udfald,
# i det uendelige. Målt 28/9: 287 poster med kun 11 unikke indhold — den
# samme linje 175 gange. Et sanseindtryk skal markere at noget ÆNDREDE sig.


def test_skal_broes_off_skriver_aldrig():
    assert erbd._skal_broes("off", True) is False
    assert erbd._skal_broes("off", False) is False


def test_skal_broes_always_er_den_gamle_adfaerd():
    assert erbd._skal_broes("always", True) is True
    assert erbd._skal_broes("always", False) is True


def test_skal_broes_first_kun_foerste_gang():
    assert erbd._skal_broes("first", True) is True
    assert erbd._skal_broes("first", False) is False


def test_mode_ukendt_falder_tilbage_til_first(monkeypatch):
    """Et slåfejl i config må ikke åbne hanen igen. Sikre valg = «first»."""
    class _Falsk:
        emotion_repair_senses_bridge_mode = "altid-agtig-slåfejl"

    monkeypatch.setattr(erbd, "load_settings", lambda: _Falsk())
    assert erbd._senses_bridge_mode() == "first"


def test_mode_ulaeselig_falder_tilbage_til_first(monkeypatch):
    def _braek():
        raise RuntimeError("config væk")

    monkeypatch.setattr(erbd, "load_settings", _braek)
    assert erbd._senses_bridge_mode() == "first"


def _koer_et_tick(monkeypatch, *, set_for: int, mode: str = "first"):
    """Kør ét tick med ét matchende mønster. Returnér (resultat, bro-kald).

    ``set_for`` er hvor mange gange dette (mønster, udfald) er set før.
    """
    bro_kald: list[dict] = []

    monkeypatch.setattr(erbd, "_last_tick_at", None)
    monkeypatch.setattr(erbd, "_ensure_default_patterns", lambda: None)
    monkeypatch.setattr(
        erbd,
        "list_active_cognitive_emotion_concept_signals",
        lambda **kw: [{"concept": "doubt", "intensity": 0.9}],
    )
    monkeypatch.setattr(
        erbd,
        "list_self_repair_patterns",
        lambda **kw: [
            {
                "pattern_id": "p-test",
                "action_type": "decision_review",
                "cooldown_seconds": 300,
                "max_attempts_per_window": 3,
                "trigger_event_kind": "emotion.doubt_spike",
                "trigger_match_json": '{"min_concept": "doubt", "min_intensity": 0.6}',
            }
        ],
    )

    def _fake_count(*, pattern_id, since_iso, outcome=None):
        # To kaldesteder med outcome: cooldown-tjekket (kort vindue) og
        # «har dette (mønster, udfald) nogensinde sket før?» (fra epoken).
        # De skelnes på since_iso — ikke på outcome, som de deler.
        if since_iso == erbd._EPOCH_ISO:
            return set_for
        return 0  # rate-limit og cooldown: ingen forsøg i vinduet → tillad

    monkeypatch.setattr(erbd, "count_recent_attempts", _fake_count)
    monkeypatch.setattr(erbd, "_execute_repair_action", lambda *a, **k: None)
    monkeypatch.setattr(erbd, "insert_self_repair_attempt", lambda **kw: {"id": 1})
    monkeypatch.setattr(
        erbd, "_bridge_repair_to_senses", lambda **kw: bro_kald.append(kw) or {"id": "s1"}
    )
    monkeypatch.setattr(erbd, "_senses_bridge_mode", lambda: mode)

    import core.services.emotional_memory_engine as eme

    monkeypatch.setattr(eme, "capture_emotional_anchor", lambda **kw: None)

    return erbd._tick_emotion_repair_bridge_inner(), bro_kald


def test_gentagelse_skrives_ikke_til_arkivet(monkeypatch):
    """Kernen: den 175. gentagelse af samme linje er ikke en ny sansning."""
    resultat, bro_kald = _koer_et_tick(monkeypatch, set_for=1)

    assert bro_kald == []
    assert resultat["senses_bridged"] == 0
    assert resultat["senses_suppressed"] == 1
    assert resultat["repairs_triggered"] == 1  # forsøget er stadig logget


def test_foerste_gang_skrives_til_arkivet(monkeypatch):
    """Første gang et (mønster, udfald) sker ER en ændring — den skal sanses."""
    resultat, bro_kald = _koer_et_tick(monkeypatch, set_for=0)

    assert len(bro_kald) == 1
    assert bro_kald[0]["pattern_id"] == "p-test"
    assert resultat["senses_bridged"] == 1
    assert resultat["senses_suppressed"] == 0


def test_mode_off_skriver_intet_selv_foerste_gang(monkeypatch):
    resultat, bro_kald = _koer_et_tick(monkeypatch, set_for=0, mode="off")

    assert bro_kald == []
    assert resultat["senses_bridged"] == 0
    assert resultat["senses_suppressed"] == 1
