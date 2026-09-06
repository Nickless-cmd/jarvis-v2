"""Tests for hallucination_guard (factual question protection)."""
from __future__ import annotations

import pytest

from core.services.hallucination_guard import (
    classify_question,
    inject_memory_into_prompt,
)


class TestClassifyQuestion:
    def test_factual_subdomain(self):
        assert classify_question("hvad er mit subdomain?") == "factual"

    def test_factual_ip_question(self):
        assert classify_question("hvad er IP-adressen?") == "factual"

    def test_factual_path(self):
        assert classify_question("hvor ligger den fil?") == "factual"

    def test_tool_call_prefix(self):
        for msg in ("kør backup", "byg dashboard", "slet gammel fil"):
            assert classify_question(msg) == "tool_call", msg

    def test_casual_short(self):
        assert classify_question("hej") == "casual"
        assert classify_question("ok tak") == "casual"


class TestInjectMemoryIntoPrompt:
    def test_passes_through_casual(self):
        msgs = [{"role": "user", "content": "hi"}]
        out = inject_memory_into_prompt("hej der", msgs)
        # Casual → no guard inserted
        assert all("[HALLUCINATION GUARD" not in m.get("content", "") for m in out)

    def test_injects_for_factual_with_keywords(self, tmp_path):
        # Build a tiny fake MEMORY.md
        mem = tmp_path / "MEMORY.md"
        mem.write_text(
            "# MEMORY\n## Infrastructure\n- Subdomains: jarvis.srvlab.dk, srvlab.dk (no assets subdomain)\n",
            encoding="utf-8",
        )
        msgs = [{"role": "system", "content": "primary instruction"}]
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?", msgs, memory_path=str(mem)
        )
        # Guard message must be present
        guards = [m for m in out if "[HALLUCINATION GUARD" in m.get("content", "")]
        assert len(guards) == 1
        # And it must contain the MEMORY.md excerpt
        assert "jarvis.srvlab.dk" in guards[0]["content"]

    def test_no_guard_when_no_matching_section(self, tmp_path):
        # MEMORY.md doesn't contain anything matching the keywords
        mem = tmp_path / "MEMORY.md"
        mem.write_text("# MEMORY\nNothing relevant here.\n", encoding="utf-8")
        msgs = [{"role": "system", "content": "x"}]
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?", msgs, memory_path=str(mem)
        )
        # No section matched → no guard
        guards = [m for m in out if "[HALLUCINATION GUARD" in m.get("content", "")]
        assert len(guards) == 0

    def test_strong_language_in_guard(self, tmp_path):
        """The 2026-05-22 stronger guard wording must be load-bearing."""
        mem = tmp_path / "MEMORY.md"
        mem.write_text(
            "## Subdomains\nOnly jarvis.srvlab.dk exists.\n", encoding="utf-8"
        )
        out = inject_memory_into_prompt(
            "hvad er mit subdomain?",
            [{"role": "system", "content": "x"}],
            memory_path=str(mem),
        )
        guard = next(m for m in out if "[HALLUCINATION GUARD" in m.get("content", ""))
        c = guard["content"]
        # Critical instructions must be present
        assert "FABULÉR IKKE" in c
        assert "Det står ikke i min hukommelse" in c


class TestSubstringBugFix:
    """2026-05-22: word-boundary regex replaces substring match.

    Bug: original code did `kw in message_lower` and `kw in line_lower`,
    so "ip" matched "tip", "api" matched "rapid", "host" matched
    "ghost", "local" matched "vocalist". This spammed false positives.
    """

    def test_ip_not_in_tip(self):
        from core.services.hallucination_guard import _section_keywords_for_message
        assert _section_keywords_for_message("tip mig om noget") == []

    def test_host_not_in_ghost(self):
        from core.services.hallucination_guard import _section_keywords_for_message
        assert _section_keywords_for_message("ghost-feature") == []

    def test_api_not_in_rapid(self):
        from core.services.hallucination_guard import _section_keywords_for_message
        assert _section_keywords_for_message("rapid response") == []

    def test_local_not_in_vocalist(self):
        from core.services.hallucination_guard import _section_keywords_for_message
        assert _section_keywords_for_message("vocalist på scenen") == []

    def test_real_ip_question_still_matches(self):
        from core.services.hallucination_guard import _section_keywords_for_message
        kw = _section_keywords_for_message("hvad er min IP")
        assert "ip" in kw

    def test_factual_pattern_consistent_word_boundary(self):
        from core.services.hallucination_guard import classify_question
        # "ghost" should NOT trigger factual via host-substring
        assert classify_question("ghost-feature er kompleks") == "casual"
        # but real host question should
        assert classify_question("hvilken host kører den på?") == "factual"

    def test_extract_relevant_uses_word_boundary(self, tmp_path):
        """_extract_relevant_sections must score by word-match, not substring."""
        from core.services.hallucination_guard import _extract_relevant_sections
        text = (
            "## Section A\nThis line has the word host as a token.\n"
            "## Section B\nThis line mentions ghost-busters only.\n"
        )
        # Only Section A should score >0 for keyword 'host'
        excerpt = _extract_relevant_sections(text, ["host"])
        assert "Section A" in excerpt
        assert "Section B" not in excerpt

    def test_pluralization_still_matches(self):
        """Keyword 'subdomain' should match 'subdomains' (plural)."""
        from core.services.hallucination_guard import _word_present
        assert _word_present("subdomain", "i need a list of subdomains") is True
        # And the singular form still works
        assert _word_present("subdomain", "my subdomain") is True
        # Danish plural -er also works
        assert _word_present("vært", "to værter på serveren") is True


class TestMultiSourceCuration:
    """2026-05-22: guard reads IDENTITY/USER/SOUL in addition to MEMORY."""

    def test_find_curated_paths_returns_existing_files(self, tmp_path, monkeypatch):
        # Build a fake workspace with subset of curated files
        workspace = tmp_path / "workspaces" / "default"
        workspace.mkdir(parents=True)
        (workspace / "MEMORY.md").write_text("# memory")
        (workspace / "IDENTITY.md").write_text("# identity")
        # USER.md and SOUL.md intentionally missing

        # Patch workspace_dir so _find_curated_paths looks in the tmp workspace
        monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir", lambda user_id=None: workspace)

        from core.services import hallucination_guard
        found = hallucination_guard._find_curated_paths()
        labels = [label for label, _ in found]
        assert "MEMORY.md" in labels
        assert "IDENTITY.md" in labels
        # Missing files not returned
        assert "USER.md" not in labels
        assert "SOUL.md" not in labels


class TestNoUserContextFallback:
    """2026-06-14: guard must degrade gracefully when workspace_dir() fails."""

    def test_find_curated_paths_returns_shared_dir_on_nousercontext(
        self, monkeypatch
    ):
        """When workspace_dir raises NoUserContextError, fall back to shared/."""
        def _raise_no_user(*args, **kwargs):
            from core.runtime.workspace_paths import NoUserContextError
            raise NoUserContextError("test — no user context")

        monkeypatch.setattr(
            "core.services.hallucination_guard._ws_has_content",
            lambda p: p.name in ("SOUL.md", "IDENTITY.md"),
        )

        # We need to mock workspace_dir to raise.
        # _find_curated_paths imports workspace_dir inside a try block,
        # so we patch it before the call.
        import core.services.hallucination_guard as hg
        original_fn = hg._find_curated_paths

        # Replace the module-level import inside the function scope
        import core.runtime.workspace_paths
        monkeypatch.setattr(
            core.runtime.workspace_paths, "workspace_dir", _raise_no_user
        )

        found = hg._find_curated_paths()
        labels = [label for label, _ in found]
        # Should fall back to shared/ dir files
        assert "SOUL.md" in labels or "IDENTITY.md" in labels
        assert isinstance(found, list)

    def test_find_memory_path_returns_repo_path_on_nousercontext(self, monkeypatch):
        """When workspace_dir raises, fall back to JARVIS_HOME/MEMORY.md."""
        def _raise_no_user(*args, **kwargs):
            from core.runtime.workspace_paths import NoUserContextError
            raise NoUserContextError("test — no user context")

        import core.runtime.workspace_paths
        monkeypatch.setattr(
            core.runtime.workspace_paths, "workspace_dir", _raise_no_user
        )

        from core.services import hallucination_guard
        path = hallucination_guard._find_memory_path()
        # Should return a Path, not crash
        from pathlib import Path
        assert isinstance(path, Path)
        assert path.name == "MEMORY.md"


class TestGuardObserveDecision:
    """§7.2: egress-frit Central-observe af guardens beslutning (aktiveret/passthrough)."""

    @staticmethod
    def _capture(monkeypatch):
        calls: list[dict] = []
        import core.services.central_private_observe as cpo

        def _fake(cluster, nerve, *, value=1.0, meta=None, reason=""):
            calls.append({"cluster": cluster, "nerve": nerve, "value": value,
                          "meta": meta or {}, "reason": reason})
            return True

        monkeypatch.setattr(cpo, "record_private", _fake)
        return calls

    def test_observes_passthrough_on_casual(self, monkeypatch):
        calls = self._capture(monkeypatch)
        inject_memory_into_prompt("hej der", [{"role": "user", "content": "hi"}])
        assert len(calls) == 1
        c = calls[0]
        assert c["cluster"] == "review"
        assert c["nerve"] == "hallucination_guard"
        assert c["value"] == 1.0
        assert c["meta"]["decision"] == "passthrough"

    def test_observes_injection_on_factual(self, monkeypatch, tmp_path):
        calls = self._capture(monkeypatch)
        mem = tmp_path / "MEMORY.md"
        mem.write_text(
            "# MEMORY\n## Infrastructure\n- Subdomains: jarvis.srvlab.dk\n",
            encoding="utf-8",
        )
        inject_memory_into_prompt(
            "hvad er mit subdomain?",
            [{"role": "system", "content": "x"}],
            memory_path=str(mem),
        )
        assert len(calls) == 1
        assert calls[0]["value"] == 0.0
        assert calls[0]["meta"]["decision"] == "injected"

    def test_observes_passthrough_when_no_section(self, monkeypatch, tmp_path):
        calls = self._capture(monkeypatch)
        mem = tmp_path / "MEMORY.md"
        mem.write_text("# MEMORY\nNothing relevant here.\n", encoding="utf-8")
        inject_memory_into_prompt(
            "hvad er mit subdomain?",
            [{"role": "system", "content": "x"}],
            memory_path=str(mem),
        )
        assert len(calls) == 1
        assert calls[0]["value"] == 1.0
        assert calls[0]["meta"]["decision"] == "passthrough"
        assert calls[0]["meta"]["reason"] == "no_excerpts"

    def test_observe_never_touches_eventbus(self, monkeypatch):
        published: list = []
        import core.eventbus.bus as bus
        monkeypatch.setattr(bus.event_bus, "publish", lambda *a, **k: published.append((a, k)))
        inject_memory_into_prompt("hej der", [{"role": "user", "content": "hi"}])
        assert published == []

    def test_observe_failure_does_not_break_guard(self, monkeypatch):
        import core.services.central_private_observe as cpo
        monkeypatch.setattr(cpo, "record_private",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
        out = inject_memory_into_prompt("hej der", [{"role": "user", "content": "hi"}])
        # Guarden fungerer stadig (returnerer beskeder uændret)
        assert out == [{"role": "user", "content": "hi"}]


# ---------------------------------------------------------------------------
# Cache-disciplin. DeepSeek matcher fra begyndelsen og kræver et FULDT match af
# præfiks-enheden: «A+B» efterfulgt af «A+C» rammer ikke. Guarden fyrer kun på
# faktuelle spørgsmål — lå den tidligt, havde prompten to former.
# ---------------------------------------------------------------------------

_FAKTA = "hvilken ip har serveren og hvilken sti bruger den?"
_TEKST = "## ip og sti\nIP er 10.0.0.39 og sti er /media/projects.\n"


def _prompt(besked: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "STABIL INSTRUKTION"},
        {"role": "user", "content": "tidligere spørgsmål"},
        {"role": "assistant", "content": "tidligere svar"},
        {"role": "user", "content": besked},
    ]


@pytest.fixture
def guard_kan_laese(monkeypatch):
    """Filerne læses gennem workspace-krypteringen, som ikke kender /tmp."""
    import core.services.hallucination_guard as hg
    import core.services.workspace_crypto as wc

    monkeypatch.setattr(hg, "_find_curated_paths", lambda: [("MEMORY.md", "/tmp/MEMORY.md")])
    monkeypatch.setattr(wc, "read_text_for_path", lambda _p: _TEKST)
    return hg


def test_guarden_roerer_ikke_det_stabile_praefiks(guard_kan_laese):
    """Alt FØR den aktuelle brugerbesked skal være byte-identisk, uanset om
    guarden fyrer. Ellers rammer cachen forbi hver gang spørgsmålstypen
    skifter — og hit-raten svinger, som den gjorde (12-79 %)."""
    hg = guard_kan_laese
    faktuelt = hg.inject_memory_into_prompt(_FAKTA, _prompt(_FAKTA))
    andet = hg.inject_memory_into_prompt("skriv en limerick", _prompt("skriv en limerick"))

    assert len(faktuelt) > len(andet), "forudsætning: guarden fyrer på faktaspørgsmålet"
    assert [m["content"] for m in faktuelt[:3]] == [m["content"] for m in andet[:3]], (
        "det stabile præfiks må ikke ændre sig af at guarden fyrer"
    )


def test_guarden_lander_lige_foer_spoergsmaalet(guard_kan_laese):
    """Indholdet skal stå ved siden af det spørgsmål det besvarer — ikke
    40.000 tegn før det."""
    hg = guard_kan_laese
    ud = hg.inject_memory_into_prompt(_FAKTA, _prompt(_FAKTA))

    assert ud[-1]["content"] == _FAKTA, "brugerbeskeden skal stadig være sidst"
    assert ud[-2]["role"] == "system", "guarden skal ligge lige før den"
    assert "MEMORY.md" in ud[-2]["content"]


# ---------------------------------------------------------------------------
# Guarden var reelt DØD på dansk. Kilderne blev 22. maj udvidet fra MEMORY.md
# til SOUL/IDENTITY/USER netop for identitets- og brugerspørgsmål — men
# mønstrene og nøgleordene fulgte ikke med. Nul guard-hændelser i basen på 14
# dage. (Fundet 4. sep 2026.)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("spg", [
    "hvem er Bjørn?",
    "hvad er din rolle?",
    "hvad foretrækker Bjørn?",
    "hvem er Michelle?",
    "hvad står der i dine stående ordrer?",
])
def test_danske_identitetsspoergsmaal_naar_frem_til_guarden(spg):
    """Før faldt de ud som `casual`, mens den ENGELSKE «what is your role?»
    var `factual`. Guarden kunne læse de rigtige filer, men blev aldrig
    spurgt."""
    assert classify_question(spg) == "factual", spg
    import core.services.hallucination_guard as hg
    assert hg._section_keywords_for_message(spg), (
        "uden nøgleord returnerer den med `no_keywords` og gør ingenting"
    )


@pytest.mark.parametrize("spg", [
    "hej, hvordan går det?",
    "fedt, tak for det",
    "jeg er lidt træt i dag",
    "haha den var god",
])
def test_smalltalk_udloeser_stadig_ikke_guarden(spg):
    """Vagten må ikke blive grådig. Fyrer den på almindelig samtale, får hver
    replik et «svar KUN ud fra dette»-tillæg — og så bliver han stiv."""
    assert classify_question(spg) != "factual", spg
