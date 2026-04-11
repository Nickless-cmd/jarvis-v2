from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import core.runtime.circadian_state as cs


def _reset():
    cs._activity_log.clear()
    cs._last_restore_check = None
    cs._current_energy = ""
    cs._last_energy_written = ""


def test_clock_baseline_morning():
    assert cs._clock_baseline(7) == "høj"


def test_clock_baseline_afternoon_dip():
    assert cs._clock_baseline(15) == "lav"


def test_clock_baseline_night():
    assert cs._clock_baseline(2) == "udmattet"


def test_drain_lowers_energy():
    _reset()
    now = datetime.now(UTC)
    # 25 events in last hour → high drain → energy drops one level
    cs._activity_log = [now - timedelta(minutes=i) for i in range(25)]
    with patch("core.runtime.circadian_state._clock_baseline", return_value="høj"):
        ctx = cs.get_circadian_context()
    assert ctx["energy_level"] == "medium"
    assert ctx["drain_label"] == "høj"


def test_no_drain_preserves_baseline():
    _reset()
    # 0 events → drain_score = 0 → no drain
    with patch("core.runtime.circadian_state._clock_baseline", return_value="høj"):
        ctx = cs.get_circadian_context()
    assert ctx["energy_level"] == "høj"
    assert ctx["drain_label"] == "lav"


def test_restore_raises_energy_after_silence():
    _reset()
    # Last event 35 min ago → beyond 30-min restore threshold
    old_time = datetime.now(UTC) - timedelta(minutes=35)
    cs._activity_log = [old_time]
    cs._current_energy = "lav"
    cs._last_energy_written = "lav"
    with patch("core.runtime.circadian_state._clock_baseline", return_value="lav"):
        ctx = cs.get_circadian_context()
    assert ctx["energy_level"] == "medium"


def test_persistence_writes_on_change(tmp_path):
    _reset()
    # Recent activity prevents restore logic from altering the baseline
    cs._activity_log = [datetime.now(UTC)]
    state_file = tmp_path / "circadian.json"
    with patch("core.runtime.circadian_state._STATE_PATH", state_file):
        with patch("core.runtime.circadian_state._clock_baseline", return_value="medium"):
            cs.get_circadian_context()
    data = json.loads(state_file.read_text())
    assert data["energy_level"] == "medium"


def test_persistence_not_written_when_unchanged(tmp_path):
    _reset()
    # Recent activity prevents restore logic from altering the baseline
    cs._activity_log = [datetime.now(UTC)]
    state_file = tmp_path / "circadian.json"
    cs._last_energy_written = "medium"  # pretend already written
    with patch("core.runtime.circadian_state._STATE_PATH", state_file):
        with patch("core.runtime.circadian_state._clock_baseline", return_value="medium"):
            cs.get_circadian_context()
    assert not state_file.exists()


def test_load_persisted_state(tmp_path):
    _reset()
    state_file = tmp_path / "circadian.json"
    state_file.write_text(json.dumps({"energy_level": "udmattet"}))
    with patch("core.runtime.circadian_state._STATE_PATH", state_file):
        result = cs.load_persisted_state()
    assert result == "udmattet"
    assert cs._current_energy == "udmattet"
