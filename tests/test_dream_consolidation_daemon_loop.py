"""Tests for drømme-konsolideringens egen kadence.

MÅLT 2026-08-30: konsolideringen blev kun vurderet når heartbeat tikkede.
På 30 dage faldt **0 af 237** heartbeat-ticks i et vindue med >= 30 min
stilhed — selvom der var **440** sådanne vinduer. Gaten krævede stilhed;
observatøren var der aldrig når der var stille. Derfor stod den stille fra
4. juni, selvom hver eneste anden gate var grøn.

Tråden her er rettelsen: den tikker på sin egen kadence og logger udfaldet,
så næste stilstand kan ses i journalen frem for at skulle måles frem.
"""

from __future__ import annotations

import logging
import threading

import pytest

import core.services.dream_consolidation_daemon as d


class TestLoopCadence:
    def test_loop_calls_tick_and_stops_on_event(self, monkeypatch) -> None:
        calls: list[float] = []
        stop = threading.Event()

        def fake_tick(seconds: float = 0.0):
            calls.append(seconds)
            stop.set()                      # stop efter første runde
            return {"skipped": True, "reason": "not-idle-1m"}

        monkeypatch.setattr(d, "tick", fake_tick)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        d.consolidation_loop(stop)
        assert calls == [0]

    def test_loop_survives_a_raising_tick(self, monkeypatch, caplog) -> None:
        """Heartbeat-kaldet lå i `except: pass` — en fejl forsvandt lydløst."""
        stop = threading.Event()
        seen = {"n": 0}

        def boom(seconds: float = 0.0):
            seen["n"] += 1
            stop.set()
            raise RuntimeError("syntese fejlede")

        monkeypatch.setattr(d, "tick", boom)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.ERROR):
            d.consolidation_loop(stop)      # må ikke kaste videre
        assert seen["n"] == 1
        assert "tick fejlede" in caplog.text

    def test_successful_run_is_logged_at_info(self, monkeypatch, caplog) -> None:
        """En drøm skal kunne ses i journalen, ikke kun i state-filen."""
        stop = threading.Event()

        def ran(seconds: float = 0.0):
            stop.set()
            return {"consolidation_id": "dream-abc123"}

        monkeypatch.setattr(d, "tick", ran)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.INFO):
            d.consolidation_loop(stop)
        assert "dream-abc123" in caplog.text
        assert "KØRTE" in caplog.text

    def test_skips_are_not_logged_at_info(self, monkeypatch, caplog) -> None:
        """En sprunget-over-runde hvert 5. minut må ikke fylde journalen."""
        stop = threading.Event()

        def skip(seconds: float = 0.0):
            stop.set()
            return {"skipped": True, "reason": "cooldown-2.0h"}

        monkeypatch.setattr(d, "tick", skip)
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        with caplog.at_level(logging.INFO):
            d.consolidation_loop(stop)
        assert "cooldown" not in caplog.text

    def test_none_result_is_handled(self, monkeypatch) -> None:
        stop = threading.Event()
        monkeypatch.setattr(d, "tick", lambda s=0.0: (stop.set(), None)[1])
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0)
        d.consolidation_loop(stop)          # må ikke kaste


class TestStartStop:
    def teardown_method(self) -> None:
        d.stop_dream_consolidation_daemon()

    def test_start_spawns_a_named_daemon_thread(self, monkeypatch) -> None:
        monkeypatch.setattr(d, "tick", lambda s=0.0: {"skipped": True})
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0.05)
        d._DAEMON_STOP_EVENT = None
        d.start_dream_consolidation_daemon()
        assert d._DAEMON_THREAD is not None
        assert d._DAEMON_THREAD.daemon is True
        assert d._DAEMON_THREAD.name == "jarvis-dream-consolidation"

    def test_start_is_idempotent(self, monkeypatch) -> None:
        monkeypatch.setattr(d, "tick", lambda s=0.0: {"skipped": True})
        monkeypatch.setattr(d, "_LOOP_INTERVAL_SECONDS", 0.05)
        d._DAEMON_STOP_EVENT = None
        d.start_dream_consolidation_daemon()
        first = d._DAEMON_THREAD
        d.start_dream_consolidation_daemon()
        assert d._DAEMON_THREAD is first

    def test_stop_is_safe_when_never_started(self) -> None:
        d._DAEMON_STOP_EVENT = None
        d.stop_dream_consolidation_daemon()


class TestCadenceChoice:
    def test_interval_is_shorter_than_the_idle_window(self) -> None:
        """Vinduet skal opdages mens det stadig er der.

        Gaten kræver >= 30 min stilhed. Tikker vi sjældnere end det, kan et
        modent vindue nå at lukke igen uden at nogen så det — netop den fejl
        vi retter.
        """
        assert d._LOOP_INTERVAL_SECONDS < d._TRIGGER_IDLE_MINUTES * 60

    def test_interval_is_not_so_short_it_hammers(self) -> None:
        assert d._LOOP_INTERVAL_SECONDS >= 60


class TestNoDanglingHelperReferences:
    """Fanger fejlklassen der stoppede drømmene i knap tre måneder.

    D4-refaktoreringen (9e961f1d, 9. juni) fjernede ``_write_dream_note`` men
    lod kaldet i ``consolidate_now()`` stå. Hver gang idle-gaten endelig
    åbnede, styrtede konsolideringen med NameError — og fordi heartbeat-kaldet
    lå i ``except Exception: pass``, forsvandt det uden spor. Sidste vellykkede
    drøm var 4. juni, fem dage før den commit.

    En import lykkes fint med et manglende navn; det opdages først når linjen
    faktisk køres. Derfor denne statiske kontrol.
    """

    def _module_names(self, tree, module) -> set[str]:
        import ast
        defined = set(dir(module)) | set(dir(__builtins__))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    defined.add((a.asname or a.name).split(".")[0])
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
        return defined

    def test_every_private_helper_called_is_defined(self) -> None:
        import ast
        import inspect
        source = inspect.getsource(d)
        tree = ast.parse(source)
        defined = self._module_names(tree, d)

        missing: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            # Kun bare navne som _helper(...) — attributter hører til andre moduler.
            if isinstance(fn, ast.Name) and fn.id.startswith("_") and fn.id not in defined:
                missing.append(f"{fn.id} (linje {fn.lineno})")

        assert not missing, (
            "kaldes men er ikke defineret i modulet: " + ", ".join(sorted(set(missing)))
        )

    def test_the_specific_helper_that_was_lost(self) -> None:
        """Regressionsvagt for netop den funktion der forsvandt."""
        assert callable(getattr(d, "_write_dream_note", None))


class TestExtractJsonObject:
    """Syntesen faldt tilbage til en nøgleordsliste fordi parseren gav op.

    Målt 31-08: samme model gav `llm-no-json` og derefter gyldig JSON på under
    et minut. Fejlen er flakkende indpakning, ikke manglende svar — så
    udtrækket skal tåle tænknings-blokke, markdown-hegn og prosa udenom.
    """

    def test_plain_object(self) -> None:
        assert d.extract_json_object('{"a": 1}') == {"a": 1}

    def test_prose_before_and_after(self) -> None:
        raw = 'Her er min analyse:\n{"dream_hypothesis": "stilhed"}\nHåber det hjælper.'
        assert d.extract_json_object(raw) == {"dream_hypothesis": "stilhed"}

    def test_markdown_fence(self) -> None:
        raw = 'Svar:\n```json\n{"tension": "modsætning"}\n```\n'
        assert d.extract_json_object(raw) == {"tension": "modsætning"}

    def test_thinking_block_is_stripped(self) -> None:
        """Præcis compaction-fejlen fra 18-07, nu i drømmene."""
        raw = '<thinking>Jeg overvejer temaerne...{"nej": 1}</thinking>\n{"ja": 2}'
        assert d.extract_json_object(raw) == {"ja": 2}

    def test_nested_object_is_balanced_not_greedy(self) -> None:
        """'sidste }' er forkert når modellen skriver prosa bagefter."""
        raw = '{"a": {"b": 1}} og så noget mere tekst med } i'
        assert d.extract_json_object(raw) == {"a": {"b": 1}}

    def test_real_response_shape(self) -> None:
        raw = ('{\n  "dream_hypothesis": "Stilhed er ikke fravær af aktivitet.",\n'
               '  "tension": "still vs active",\n  "confidence": 0.5\n}')
        got = d.extract_json_object(raw)
        assert got["confidence"] == 0.5
        assert "Stilhed" in got["dream_hypothesis"]

    @pytest.mark.parametrize("raw", [
        "", None, "slet ingen JSON her", "{ ubalanceret", "[1, 2, 3]",
    ])
    def test_degenerate_input_returns_none(self, raw) -> None:
        assert d.extract_json_object(raw) is None

    def test_never_raises(self) -> None:
        assert d.extract_json_object({"ikke": "en streng"}) is None


class TestThemeQuality:
    """Han drømte om sin egen skabelon.

    Målt 31-08: 33 af 40 inder-liv-fragmenter begynder med samme sætning
    ("[carry] Diverse inner threads (N types) are all still active..."), så
    otte ord fik vægt 33 hver mens chattens hyppigste nåede 15. Temaerne blev
    'still', 'types', 'diverse'. Dubletfjernelse duede ikke — fragmenterne ER
    forskellige (Jaccard-median 0,36); de deler kun begyndelsen.
    """

    def test_boilerplate_tokens_are_dropped(self) -> None:
        from collections import Counter
        counter = Counter({"skabelon": 33, "indhold": 15, "sjaelden": 3})
        out = d.drop_boilerplate_tokens(counter, fragment_count=76)
        assert "skabelon" not in out          # 43 % af fragmenterne
        assert out["indhold"] == 15           # 20 % — beholdes
        assert out["sjaelden"] == 3

    def test_small_corpus_is_left_alone(self) -> None:
        """Med få fragmenter er en høj andel ikke støj — det ER temaet."""
        from collections import Counter
        counter = Counter({"alt": 4})
        assert d.drop_boilerplate_tokens(counter, fragment_count=5) == counter

    def test_boundary_is_inclusive(self) -> None:
        from collections import Counter
        counter = Counter({"paa_graensen": 33})
        out = d.drop_boilerplate_tokens(counter, fragment_count=100,
                                        max_doc_frequency=0.33)
        assert out["paa_graensen"] == 33      # præcis paa loftet beholdes

    def test_truncated_last_word_is_dropped(self) -> None:
        """'materi' (af 'materiale') stod som tema nr. 2 før dette værn."""
        toks = d._fragment_tokens("bounded internal materi")
        assert "materi" not in toks

    def test_complete_sentence_keeps_its_last_word(self) -> None:
        toks = d._fragment_tokens("bounded internal materiale.")
        assert "materiale" in toks

    @pytest.mark.parametrize("weak", ["siden", "stadig", "still", "records"])
    def test_weak_filler_words_are_stopwords(self, weak: str) -> None:
        assert weak in d._STOPWORDS

    @pytest.mark.parametrize("text", ["", None, "   ", "a"])
    def test_fragment_tokens_degenerate_input(self, text) -> None:
        assert d._fragment_tokens(text) == []


class TestChronicleFlag:
    """Posten meldte chronicle=false selvom teksten stod i filen.

    Målt 31-08: `synthesis-*.md` indeholdt kronik-fragmentet ("I nat drømte jeg
    om still...") mens `d4_synthesis` sagde chronicle=false. Branchen satte kun
    dream_note. Flaget løj — kroniken manglede ikke.
    """

    def test_chronicle_flag_follows_the_written_text(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(d, "_dreams_dir", lambda: tmp_path)
        out = d._produce_dream_artifacts(
            {"dream_hypothesis": "", "tension": "spænding",
             "chronicle_fragment": "I nat stod ordet still stille i mig.",
             "thematic_insight": "", "confidence": 0.5},
            "dream-test01", [{"theme": "still"}],
        )
        assert out["dream_note"] is True
        assert out["chronicle"] is True
        written = "\n".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("synthesis-*.md"))
        assert "I nat stod ordet still stille i mig." in written

    def test_no_chronicle_text_means_flag_stays_false(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(d, "_dreams_dir", lambda: tmp_path)
        out = d._produce_dream_artifacts(
            {"dream_hypothesis": "", "tension": "", "chronicle_fragment": "",
             "thematic_insight": "kun en indsigt", "confidence": 0.5},
            "dream-test02", [{"theme": "x"}],
        )
        assert out["chronicle"] is False
        assert out["dream_note"] is True
