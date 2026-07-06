from unittest import mock
from core.services import central_oracle as co
from core.services.central_timeseries import Sample


def _series(values, step_s=600):
    # ts stigende med step_s; ældst først
    base = 1_700_000_000
    return [Sample(ts=__import__("datetime").datetime.fromtimestamp(
        base + i * step_s, tz=__import__("datetime").timezone.utc).isoformat(),
        value=float(v)) for i, v in enumerate(values)]


def test_approaching_threshold_gives_eta():
    rising = _series([50, 60, 70, 80, 90])   # stiger 10 pr. 600s mod 100
    with mock.patch("core.services.central_timeseries.recent", return_value=rising):
        p = co._project({"cluster": "system", "nerve": "excess", "threshold": 100.0,
                         "dir": "up", "label": "x"})
    assert p["state"] == "approaching" and p["eta_hours"] is not None and p["eta_hours"] > 0


def test_already_crossed_is_flagged():
    hot = _series([90, 95, 100, 105, 110])
    with mock.patch("core.services.central_timeseries.recent", return_value=hot):
        p = co._project({"cluster": "system", "nerve": "excess", "threshold": 100.0,
                         "dir": "up", "label": "x"})
    assert p["state"] == "crossed" and p["eta_hours"] == 0.0


def test_moving_away_is_stable():
    falling = _series([90, 80, 70, 60, 50])
    with mock.patch("core.services.central_timeseries.recent", return_value=falling):
        p = co._project({"cluster": "system", "nerve": "excess", "threshold": 100.0,
                         "dir": "up", "label": "x"})
    assert p["state"] == "stable" and p["eta_hours"] is None


def test_too_few_points_returns_none():
    with mock.patch("core.services.central_timeseries.recent", return_value=_series([1, 2])):
        assert co._project({"cluster": "system", "nerve": "excess", "threshold": 100.0,
                            "dir": "up", "label": "x"}) is None


def test_record_observes_metadata_only():
    obs = []
    fc = mock.MagicMock(); fc.observe.side_effect = lambda e: obs.append(e)
    with mock.patch("core.services.central_timeseries.recent", return_value=[]), \
            mock.patch("core.services.central_core.central", return_value=fc):
        co.record_oracle()
    assert obs and obs[0]["nerve"] == "oracle"
    assert set(obs[0]) <= {"cluster", "nerve", "kind", "approaching", "crossed"}
