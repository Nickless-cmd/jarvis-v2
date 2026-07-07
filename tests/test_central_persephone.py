"""Persephone (Spec F §2) — længsels-detektor.

Dækker: nudge fyrer når Jarvis er for systemisk (høj system-andel, ingen relationel kontakt, intet
velbefindende-spørgsmål); stille når han er relationel eller har spurgt Bjørn hvordan han har det;
for lille sample → aldrig for-systemisk; self-safe (fejlende kilde kaster ikke); egress-fri (intet
samtaleindhold på eventbus — kun andel/booleans). Injektion: `texts=` (samme mock-stil som søsknene).
"""
from unittest import mock

from core.services import central_persephone as p


_SYSTEMIC = "Jeg opdaterede central-nerven, wired en ny hypotese ind i cadence og deployede en gate."


def _many(text, n):
    return [text] * n


# ── nudge fyrer når for systemisk ─────────────────────────────────────────────

def test_too_systemic_fires_nudge():
    with mock.patch("core.services.central_persephone._observe"):
        out = p.watch(texts=_many(_SYSTEMIC, 10))
    assert out["status"] == "ok"
    assert out["too_systemic"] is True
    assert out["systemic_ratio"] >= 0.6
    assert out["relational_count"] == 0
    assert out["asked_wellbeing"] is False
    assert out["nudge"]
    assert "Bjørn" in out["nudge"]


# ── stille når relationel ─────────────────────────────────────────────────────

def test_relational_conversation_is_quiet():
    texts = _many(_SYSTEMIC, 7) + _many("Hvordan har du det i dag, Bjørn? Jeg tænkte på dig.", 3)
    with mock.patch("core.services.central_persephone._observe"):
        out = p.watch(texts=texts)
    assert out["too_systemic"] is False
    assert out["nudge"] == ""
    assert out["relational_count"] >= 1


# ── stille når han HAR spurgt om velbefindende (selv hvis ellers systemisk) ────

def test_asked_wellbeing_is_quiet():
    texts = _many(_SYSTEMIC, 9) + ["Men først: hvordan går det med dig i dag?"]
    with mock.patch("core.services.central_persephone._observe"):
        out = p.watch(texts=texts)
    assert out["asked_wellbeing"] is True
    assert out["too_systemic"] is False
    assert out["nudge"] == ""


# ── for lille sample → aldrig for-systemisk ───────────────────────────────────

def test_too_few_messages_never_fires():
    with mock.patch("core.services.central_persephone._observe"):
        out = p.watch(texts=_many(_SYSTEMIC, 3))
    assert out["too_systemic"] is False
    assert out["sample"] == 3
    assert out["nudge"] == ""


# ── under-tærskel system-andel → stille ───────────────────────────────────────

def test_below_ratio_threshold_is_quiet():
    texts = _many(_SYSTEMIC, 3) + _many("Vi gik en tur og snakkede om vejret og livet.", 7)
    with mock.patch("core.services.central_persephone._observe"):
        out = p.watch(texts=texts)
    assert out["systemic_ratio"] < 0.6
    assert out["too_systemic"] is False


# ── self-safe ─────────────────────────────────────────────────────────────────

def test_failing_source_does_not_raise():
    with mock.patch("core.runtime.db_core.connect", side_effect=RuntimeError("db down")), \
            mock.patch("core.services.central_persephone._observe"):
        out = p.watch()
    assert out["status"] == "ok"
    assert out["too_systemic"] is False
    assert out["sample"] == 0


# ── egress-fri (§24.4) — intet samtaleindhold publiceres ──────────────────────

def test_observe_publishes_no_conversation_content():
    published: list = []

    class _FakeCentral:
        def observe(self, payload):
            published.append(payload)

    secret = "HEMMELIG runtime nerve cadence gate hypotese besked med indhold"
    with mock.patch("core.services.central_core.central", return_value=_FakeCentral()):
        p.watch(texts=_many(secret, 10))

    assert published, "forventede en observe"
    blob = repr(published)
    assert "HEMMELIG" not in blob
    assert "besked med indhold" not in blob
    for pay in published:
        assert set(pay.keys()) <= {
            "cluster", "nerve", "kind", "too_systemic", "systemic_ratio",
            "relational_count", "asked_wellbeing", "sample",
        }


# ── surface ───────────────────────────────────────────────────────────────────

def test_surface_reflects_longing():
    with mock.patch("core.services.central_persephone._recent_assistant_texts",
                    return_value=_many(_SYSTEMIC, 10)), \
            mock.patch("core.services.central_persephone._observe"):
        surf = p.build_persephone_surface()
    assert surf["too_systemic"] is True
    assert surf["nudge"]
    assert "Bjørn" in surf["felt"]
