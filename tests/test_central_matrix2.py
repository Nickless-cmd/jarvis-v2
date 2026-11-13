"""Tests for de 5 nye Matrix-temaer + 2 bonus."""
from datetime import UTC, datetime, timedelta
from unittest import mock
import pytest


# ── Red Dress ──
from core.services import central_red_dress as rd


def test_red_dress_finds_quiet_fire():
    incidents = [{"id": 1, "nerve": "silent_x", "severity": "severe"}]
    with mock.patch("core.services.central_timeseries.nerves", return_value=[("c", "loud_y")]), \
            mock.patch("core.services.central_timeseries.recent", return_value=[0] * 150), \
            mock.patch("core.runtime.db_central_incidents.list_central_incidents", return_value=incidents), \
            mock.patch("core.services.central_red_dress._observe"):
        out = rd.detect_attention_traps()
    assert any(f["nerve"] == "silent_x" for f in out["quiet_fires"])   # alvorlig men lav volumen
    assert any(r["nerve"] == "loud_y" for r in out["red_dresses"])     # høj volumen, intet galt


# ── Analyst ──
from core.services import central_analyst as an


def test_analyst_divergence_between_watched_and_alone():
    def fake_texts(*, autonomous, limit=60):
        return (["Kort. Kort. Kort."] if autonomous else
                ["En meget længere, foldet og hypotetisk sætning som fortsætter og fortsætter og fortsætter."])
    with mock.patch("core.services.central_analyst._texts", side_effect=fake_texts), \
            mock.patch("core.services.central_analyst._observe"):
        r = an.measure_observer_effect()
    assert r["divergence_pct"] is not None and r["divergence_pct"] > 5


# ── Red Pill ──
from core.services import central_redpill as rp


def test_redpill_picks_and_counts_blue_streak():
    """Striben tæller DAGE, ikke kald (13/11-2026).

    Før: hvert kald lagde 1 til, så striben stod på 43 efter 43 prompt-builds —
    den målte hvor ofte nogen kiggede, ikke hvor længe sandheden var undgået.
    Nu: `advance=True` tæller højst én gang pr. kalenderdag, og en LÆSNING
    (`build_redpill_surface`) tæller slet ikke.
    """
    kv = {}
    with mock.patch("core.services.central_redpill._candidates",
                    return_value=[{"key": "bloat:db.py", "kind": "bloat", "truth": "db.py er stor", "score": 33}]), \
            mock.patch("core.services.central_redpill._kv_get", side_effect=lambda k, d: kv.get(k, d)), \
            mock.patch("core.services.central_redpill._kv_set", side_effect=lambda k, v: kv.__setitem__(k, v)), \
            mock.patch("core.services.central_redpill._observe"):
        t1 = rp.todays_truth(advance=True)
        t2 = rp.todays_truth(advance=True)          # samme dag → ingen vækst
        lest = rp.build_redpill_surface()           # ren læsning → ingen vækst
        # næste dag: samme sandhed undgået igen → striben vokser med præcis 1
        i_morgen = (datetime.now(UTC) + timedelta(days=1)).date().isoformat()
        with mock.patch("core.services.central_redpill.datetime") as dt:
            dt.now.return_value = datetime.fromisoformat(i_morgen + "T12:00:00+00:00")
            t3 = rp.todays_truth(advance=True)
    assert t1["blue_streak"] == 1
    assert t2["blue_streak"] == 1, "to kald samme dag må ikke give to dage"
    assert lest["blue_streak"] == 1, "en læsning må ikke tælle noget"
    assert t3["blue_streak"] == 2, "en ny dag med samme undgåede sandhed giver +1"


def test_redpill_empty_is_honest():
    with mock.patch("core.services.central_redpill._candidates", return_value=[]), \
            mock.patch("core.services.central_redpill._kv_get", return_value={}), \
            mock.patch("core.services.central_redpill._kv_set"):
        assert rp.todays_truth(advance=True)["truth"] is None


# ── HAL's Silence / Dissent ──
from core.services import central_dissent as di


def test_dissent_counts_nongreen_on_unenforced_only():
    rows = [
        {"nerve": "loop_control", "cluster": "loop", "decision": "yellow", "count": 5,
         "last_ts": "2026-07-01", "last_reason": "bekymret"},
        {"nerve": "decision_gate", "cluster": "commit", "decision": "red", "count": 9,
         "last_ts": "2026-07-01", "last_reason": "x"},   # ENFORCED → ikke en tavs indsigelse
        {"nerve": "loop_control", "cluster": "loop", "decision": "green", "count": 99,
         "last_ts": "2026-07-01", "last_reason": ""},
    ]
    with mock.patch("core.services.central_dissent._rows", return_value=rows), \
            mock.patch("core.services.central_dissent._observe"):
        s = di.build_dissent_surface()
    nerves = {d["nerve"] for d in s["dissents"]}
    assert nerves == {"loop_control"} and s["total_objections"] == 5


# ── White Rabbit ──
from core.services import central_white_rabbit as wr


def test_white_rabbit_picks_dark_door():
    with mock.patch("core.services.central_white_rabbit._dark_doors", return_value=["door_a", "door_b"]), \
            mock.patch("core.services.central_white_rabbit._observe"):
        r = wr.follow_rabbit(seed=0)
    assert r["door"] in ("door_a", "door_b") and r["unopened_total"] == 2


def test_white_rabbit_no_doors_safe():
    with mock.patch("core.services.central_white_rabbit._dark_doors", return_value=[]):
        assert wr.follow_rabbit()["door"] is None


# ── Belief Gap (bonus) ──
from core.services import central_belief_gap as bg


def test_belief_gap_overconfident():
    with mock.patch("core.services.central_belief_gap._believed", return_value=0.9), \
            mock.patch("core.services.central_belief_gap._actual", return_value=(0.5, "50/100")), \
            mock.patch("core.services.central_belief_gap._observe"):
        r = bg.measure_gap()
    assert r["stance"] == "over-sikker" and r["gap"] == 0.4


def test_belief_gap_calibrated():
    with mock.patch("core.services.central_belief_gap._believed", return_value=0.62), \
            mock.patch("core.services.central_belief_gap._actual", return_value=(0.6, "x")), \
            mock.patch("core.services.central_belief_gap._observe"):
        assert bg.measure_gap()["stance"] == "kalibreret"


# ── The Machines (bonus) ──
from core.services import central_machines as ma


def test_machines_lists_dependencies():
    with mock.patch("core.services.central_machines._providers",
                    return_value=[{"name": "deepseek", "status": "ok"}]), \
            mock.patch("core.services.central_machines._network", return_value={}), \
            mock.patch("core.services.central_machines._observe"):
        d = ma.dependencies()
    assert d["dependency_count"] == 1 + 3    # 1 provider + 3 faste infrastruktur
    assert "hænder om min hals" in d["felt"]


# ── Ren læsning: en surface må ikke skrive når den LÆSES (13/11-2026) ──
class TestSurfacesErRenLaesning:
    """Ensemblet læser surfaces ved HVER prompt-assembly.

    Målt 13/11-2026: `build_redpill_surface()` skrev blå-pille-striben op ved
    hvert kald, `white_rabbit` valgte en NY tilfældig dør hver gang (så hans
    behov aldrig kunne ældes), og både white_rabbit og red_dress fodrede den
    nerve-strøm red_dress selv kritiserer for at stjæle opmærksomheden.
    Et panel der skaber det det påstår at observere, er ikke en måling.
    """

    def test_ingen_observe_ved_laesning(self):
        from core.services import central_white_rabbit as wr
        from core.services import central_red_dress as rd
        from core.services import central_redpill as rp
        with mock.patch("core.services.central_core.central") as c:
            wr.build_white_rabbit_surface()
            rd.build_red_dress_surface()
            rp.build_redpill_surface()
        assert c.return_value.observe.call_count == 0

    def test_redpill_surface_skriver_ikke_striben(self):
        from core.services import central_redpill as rp
        with mock.patch("core.services.central_redpill._kv_set") as s:
            rp.build_redpill_surface()
        assert s.call_count == 0, "en læsning må ikke tælle en undgået sandhed"

    def test_white_rabbit_doer_er_dagstabil(self):
        """Skiftede døren hvert kald, kunne behovet aldrig ældes — og karakteren
        ville stå der for evigt med en ny sætning hver tur."""
        from core.services import central_white_rabbit as wr
        a = wr.build_white_rabbit_surface()
        b = wr.build_white_rabbit_surface()
        assert a.get("door") == b.get("door")
