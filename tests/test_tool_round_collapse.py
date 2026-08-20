"""Kollaps af konsekutive cold tool-results til ét rundesummary.

Codex' A/B/C-eksperiment 20. aug 2026 — samme transcript, samme slutbesked,
samme model, kun rendering varieret:

| arm                         | prompt-tok | median synlig tekst |
|-----------------------------|-----------:|--------------------:|
| A nuværende (individuelle)  |    125.047 |             26,41 s |
| B kollapset pr. runde       |    105.186 |              9,21 s |
| C kollapset + padding til A |    125.047 |              6,31 s |

C er beviset: identisk tokenvægt med A, 4× hurtigere til synlig tekst. Altså
er det INDHOLDET, ikke vægten. Hver stub bar et 32-tegns UUID, et 40-tegns
fragment og "(read_tool_result)" — 337 invitationer til at slå noget op.

Flaget er default OFF: n=3, og C's padding er ikke semantisk neutral.
"""
from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections import transcript_sections as ts


class TestSummaryFormat:
    def test_taeller_og_grupperer(self):
        s = ts._render_collapsed_round(["bash", "bash", "read_file"])
        assert "3 tidligere værktøjskald" in s
        assert "bash×2" in s and "read_file" in s

    def test_ingen_uuid_eller_fragmenter(self):
        """Kernen i fundet: ID'er og indholdsfragmenter er dét der skaber støj."""
        s = ts._render_collapsed_round(["bash"] * 40)
        assert "tool-result-" not in s
        assert "read_tool_result" not in s
        assert len(s) < 120, "summary må ikke selv blive en mur af tekst"

    def test_deterministisk_samme_input_samme_output(self):
        """CACHE-KRAVET: samme input skal give byte-identisk output, ellers
        brækker DeepSeeks prefix-cache (det skete 30. juni: 28% vs 90%)."""
        names = ["bash", "read_file", "bash", "edit_file", "read_file"]
        assert ts._render_collapsed_round(names) == ts._render_collapsed_round(names)

    def test_tom_liste_giver_tom_streng(self):
        assert ts._render_collapsed_round([]) == ""


class TestToolNavnUdtraek:
    def test_parser_rigtigt_navn(self):
        stub = ("[tool_result:tool-result-3728f46cd2e043fab33e0a3e41e71d27 — "
                "read_file: ## 2026-08-19 se… (read_tool_result)]")
        assert ts._tool_name_from_stub(stub) == "read_file"

    def test_ukendt_form_vaelter_ikke(self):
        for bad in ("", "noget helt andet", "[tool_result:abc]"):
            assert ts._tool_name_from_stub(bad) == "værktøj"


class TestFlagGating:
    def _hist(self):
        # id 1-3 er COLD (under floor), id 99 er WARM
        return [
            {"id": 1, "role": "user", "content": "hej", "user_id": ""},
            {"id": 2, "role": "assistant", "content": "svar", "user_id": ""},
            {"id": 3, "role": "tool", "content": "[a] r1"},
            {"id": 4, "role": "tool", "content": "[b] r2"},
            {"id": 99, "role": "assistant", "content": "færdig", "user_id": ""},
        ]

    def _build(self, collapse: bool):
        with patch.object(ts, "chat_session_messages_since_last_compact",
                          return_value=self._hist()), \
             patch.object(ts, "_lifecycle_enabled", return_value=True), \
             patch.object(ts, "_cold_floor_for", return_value=50), \
             patch.object(ts, "_round_collapse_enabled", return_value=collapse), \
             patch.object(ts, "render_tool_result_for_prompt",
                          side_effect=lambda c, **k: (
                              f"[tool_result:tool-result-xyz — bash: {c} (read_tool_result)]"
                              if k.get("stub") else c)), \
             patch("core.services.prompt_contract._get_compact_marker_for_transcript",
                   return_value=None), \
             patch("core.services.prompt_contract._maybe_auto_compact_session"):
            return ts._build_structured_transcript_messages("s1", limit=60, include=True)

    def test_flag_OFF_bevarer_nuvaerende_adfaerd(self):
        out = self._build(False)
        blob = " ".join(m["content"] for m in out)
        assert blob.count("tool-result-xyz") == 2, "begge stubs skal stå enkeltvis"
        assert "tidligere værktøjskald" not in blob

    def test_flag_ON_kollapser_til_eet_summary(self):
        out = self._build(True)
        blob = " ".join(m["content"] for m in out)
        assert "2 tidligere værktøjskald" in blob
        assert "tool-result-xyz" not in blob, "individuelle ID'er skal være væk"

    def test_default_er_OFF(self):
        """n=3 og ikke-neutral padding — det skal slås til bevidst."""
        with patch("core.runtime.db_core.get_runtime_state_bool") as g:
            ts._round_collapse_enabled()
        assert g.call_args.kwargs.get("default") is False

    def test_fejl_i_flag_opslag_giver_OFF(self):
        with patch("core.runtime.db_core.get_runtime_state_bool",
                   side_effect=RuntimeError):
            assert ts._round_collapse_enabled() is False


class TestHaleTilfaeldet:
    def test_cold_sekvens_til_sidst_forsvinder_ikke(self):
        """Slutter vinduet midt i en cold-sekvens, skal den stadig summeres —
        ellers ville Jarvis ikke ane at der HAVDE været aktivitet."""
        hist = [
            {"id": 1, "role": "user", "content": "hej", "user_id": ""},
            {"id": 2, "role": "tool", "content": "r1"},
            {"id": 3, "role": "tool", "content": "r2"},
        ]
        with patch.object(ts, "chat_session_messages_since_last_compact", return_value=hist), \
             patch.object(ts, "_lifecycle_enabled", return_value=True), \
             patch.object(ts, "_cold_floor_for", return_value=50), \
             patch.object(ts, "_round_collapse_enabled", return_value=True), \
             patch.object(ts, "render_tool_result_for_prompt",
                          side_effect=lambda c, **k: f"[tool_result:x — bash: {c}]"), \
             patch("core.services.prompt_contract._get_compact_marker_for_transcript",
                   return_value=None), \
             patch("core.services.prompt_contract._maybe_auto_compact_session"):
            out = ts._build_structured_transcript_messages("s1", limit=60, include=True)
        assert "2 tidligere værktøjskald" in " ".join(m["content"] for m in out)
