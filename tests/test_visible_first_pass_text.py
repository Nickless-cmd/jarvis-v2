"""Tests for core/services/visible_first_pass_text.py.

Udskilt fra visible_runs.py (7.078 linjer) efter Boy Scout-reglen. Objektet
bærer to ansvar der altid har fulgt hinanden: den tekst brugeren FAKTISK så, og
vagten mod model-repetitionsløkker.
"""

from __future__ import annotations

import pytest

from core.services.visible_first_pass_text import (
    CHECK_INTERVAL_CHARS,
    FirstPassText,
)


class TestAkkumulering:
    def test_tom_ved_start(self) -> None:
        f = FirstPassText()
        assert f.text == ""
        assert len(f) == 0
        assert not f

    def test_samler_deltas_i_raekkefoelge(self) -> None:
        f = FirstPassText()
        for d in ("Jeg ", "tjekker ", "det."):
            f.feed(d)
        assert f.text == "Jeg tjekker det."
        assert len(f) == 16
        assert f

    def test_tomme_deltas_ignoreres(self) -> None:
        f = FirstPassText()
        assert f.feed("") == (False, "")
        assert f.feed(None) == (False, "")   # type: ignore[arg-type]
        assert f.text == ""


class TestVagten:
    def test_tjekker_ikke_foer_taersklen(self, monkeypatch) -> None:
        """Vagten koster — den må ikke køre pr. token."""
        kald = []
        monkeypatch.setattr("core.services.stream_degeneration.check_degeneration",
                            lambda t: (kald.append(t), (False, ""))[1], raising=False)
        f = FirstPassText()
        f.feed("x" * (CHECK_INTERVAL_CHARS - 1))
        assert kald == []

    def test_tjekker_naar_taersklen_naas(self, monkeypatch) -> None:
        kald = []
        monkeypatch.setattr("core.services.stream_degeneration.check_degeneration",
                            lambda t: (kald.append(t), (False, ""))[1], raising=False)
        f = FirstPassText()
        f.feed("x" * CHECK_INTERVAL_CHARS)
        assert len(kald) == 1

    def test_melder_degeneration_videre(self, monkeypatch) -> None:
        monkeypatch.setattr("core.services.stream_degeneration.check_degeneration",
                            lambda t: (True, "gentagelsesloekke"), raising=False)
        f = FirstPassText()
        assert f.feed("y" * CHECK_INTERVAL_CHARS) == (True, "gentagelsesloekke")

    def test_taelleren_nulstilles_mellem_spring(self, monkeypatch) -> None:
        kald = []
        monkeypatch.setattr("core.services.stream_degeneration.check_degeneration",
                            lambda t: (kald.append(len(t)), (False, ""))[1], raising=False)
        f = FirstPassText()
        for _ in range(3):
            f.feed("z" * CHECK_INTERVAL_CHARS)
        assert kald == [CHECK_INTERVAL_CHARS, CHECK_INTERVAL_CHARS * 2,
                        CHECK_INTERVAL_CHARS * 3]

    def test_vagten_maa_aldrig_tage_svaret_med_i_faldet(self, monkeypatch) -> None:
        def boom(_t):
            raise RuntimeError("vagt nede")
        monkeypatch.setattr("core.services.stream_degeneration.check_degeneration",
                            boom, raising=False)
        f = FirstPassText()
        assert f.feed("q" * CHECK_INTERVAL_CHARS) == (False, "")
        assert len(f) == CHECK_INTERVAL_CHARS   # teksten er intakt
