"""Tests for the compaction summariser's mechanical fallback (audit 2026-07-23).

When the cheap-lane summariser returns nothing usable, the fallback must NOT
collapse the whole arc into 200-char stubs — user turns (the intent) are kept
fuller than assistant turns, and the raw DB record is referenced.
"""

from __future__ import annotations

from unittest.mock import patch

from core.services.prompt_sections import transcript_sections as ts


def _fallback_summary(old_msgs):
    # Force the LLM path to yield nothing usable → mechanical fallback fires.
    with patch("core.context.compact_llm.call_compact_llm", return_value=""), \
         patch("core.context.compaction_policy.summary_looks_valid", return_value=False), \
         patch("core.context.compaction_policy.extract_summary", return_value=""), \
         patch("core.context.compaction_policy.fold_old_tool_results", side_effect=lambda m, keep=0: (m, [])), \
         patch("core.context.compaction_policy.build_structured_summary_prompt", return_value="x"), \
         patch("core.context.kompaktering._ground_truth_for", return_value=""):
        fn = ts._make_structured_summariser(None, session_id="s1")
        return fn(old_msgs)


def test_fallback_keeps_user_turns_fuller_than_assistant():
    long_user = "u" * 900
    long_asst = "a" * 900
    out = _fallback_summary([
        {"role": "user", "content": long_user},
        {"role": "assistant", "content": long_asst},
    ])
    assert "<summary>" in out and "</summary>" in out
    # User kept up to 800, assistant only up to 400.
    assert out.count("u") >= 780
    assert 380 <= out.count("a") <= 430


def test_fallback_never_empty_and_references_raw():
    out = _fallback_summary([{"role": "user", "content": "hello"}])
    assert out.strip().startswith("<summary>")
    assert "raw messages remain" in out.lower()
    assert "[user] hello" in out


def test_reasoning_replay_cappes_ved_2400():
    """Reasoning-replay er et API-krav (Deepseek 400'er uden feltet — 949712ba),
    men længden er ligegyldig for API'et. 52d6563e bumpede cappen til 8000 chars
    sammen med tekst-caps; målt 19. aug 2026 kostede det 14,6k tokens stale
    tænkning pr. tur (31% af transkriptet). Tilbage til 2400 — feltet er der,
    vægten er væk."""
    long_reasoning = "tænk " * 2000  # 10.000 chars
    history = [
        {"id": 1, "role": "user", "content": "hej", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "assistant", "content": "svar", "user_id": "",
         "reasoning_content": long_reasoning},
    ]
    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=history), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript",
               return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        out = ts._build_structured_transcript_messages("s-reason", limit=60, include=True)
    replayed = [m for m in out if m.get("reasoning_content")]
    assert replayed, "assistant-turnens reasoning_content skal stadig være der (API-krav)"
    assert len(replayed[0]["reasoning_content"]) <= 2400


# ─────────────────────────────────────────────────────────────────────────────
# Absolutte tidsstempler i transskriptet (målt udækket 22/10-2026).
#
# Funktionen er cache-stabil med vilje: den skriver et FAST klokkeslæt, ikke en
# relativ alder. En relativ tekst ville ændre sig hver tur og ugyldiggøre
# DeepSeeks præfiks-cache. Det er hele grunden til at den findes, og det er
# præcis det en test skal fastholde.
# ─────────────────────────────────────────────────────────────────────────────


def test_gyldig_timestamp_prefikses_med_kobenhavnsk_klokkeslaet():
    ud = ts._prefix_absolute_transcript_time("hej", "2026-07-15T12:00:00+00:00")
    assert ud == "[2026-07-15 14:00] hej"


def test_DST_er_historisk_sandt_ikke_dagens_offset():
    """Sommer og vinter har forskelligt offset, og det skal følge INSTANTET —
    ikke den offset der gælder når prompten bygges. Ellers ville en gammel
    sommertur få vintertid, og tidsstemplet ville lyve om hvornår den skete.
    """
    sommer = ts._prefix_absolute_transcript_time("x", "2026-07-15T12:00:00+00:00")
    vinter = ts._prefix_absolute_transcript_time("x", "2026-01-15T12:00:00+00:00")
    assert sommer.startswith("[2026-07-15 14:00]"), sommer   # CEST = +02
    assert vinter.startswith("[2026-01-15 13:00]"), vinter   # CET  = +01


def test_naiv_timestamp_laeses_som_UTC():
    """Legacy-rækker kan mangle tidszone. De må ikke fortolkes som lokal tid —
    så ville de flytte sig med maskinens zone."""
    assert ts._prefix_absolute_transcript_time("x", "2026-07-15T12:00:00") == (
        "[2026-07-15 14:00] x")


def test_tom_eller_manglende_timestamp_lader_indholdet_vaere():
    assert ts._prefix_absolute_transcript_time("hej", None) == "hej"
    assert ts._prefix_absolute_transcript_time("hej", "") == "hej"
    assert ts._prefix_absolute_transcript_time("hej", "   ") == "hej"


def test_ugyldig_timestamp_vaelter_ikke_prompten():
    """Transskript-samling må ALDRIG fejle på dårlig legacy-metadata. En
    exception her ville koste hele turen, ikke bare ét tidsstempel."""
    for raa in ("i går", "2026-13-45T99:99:99", "0001-01-01T00:00:00+99:00"):
        assert ts._prefix_absolute_transcript_time("hej", raa) == "hej", raa


def test_prefixet_er_BYTE_STABILT_mellem_to_bygninger():
    """Kernen i hvorfor funktionen bruger et absolut stempel: to bygninger af
    samme besked skal give identiske bytes, ellers brister cache-præfikset."""
    a = ts._prefix_absolute_transcript_time("samme", "2026-10-22T05:00:00+00:00")
    b = ts._prefix_absolute_transcript_time("samme", "2026-10-22T05:00:00+00:00")
    assert a == b


def test_begge_samtaleroller_beholder_tid_i_modellens_transskript():
    """Outputfilteret må aldrig koste Jarvis den tidsfornemmelse det beskytter."""
    history = [
        {
            "id": 1, "role": "user", "content": "hej", "user_id": "",
            "reasoning_content": "", "created_at": "2026-10-23T19:58:00+00:00",
        },
        {
            "id": 2, "role": "assistant", "content": "hej igen", "user_id": "",
            "reasoning_content": "", "created_at": "2026-10-23T19:59:00+00:00",
        },
    ]
    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=history), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript",
               return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        out = ts._build_structured_transcript_messages(
            "s-tid", limit=60, include=True,
        )
    assert out[0]["content"] == "[2026-10-23 21:58] hej"
    assert out[1]["content"] == "[2026-10-23 21:59] hej igen"


# ─────────────────────────────────────────────────────────────────────────────
# Afgjorte godkendelses-kort i transskriptet (målt 22/11-2026).
#
# `approval_request` blev slettet fra prompten som «en UI-række». Men et AFGJORT
# kort bærer udfaldet, og når det forsvandt, stod det efterfølgende tool-svar
# tilbage som et svar på ingenting. Målt i samtalen
# chat-f5a6b0d9630c425fb8e4f6220c5fcb81: to kort blev godkendt 22:37 — 10-15 min
# efter turen havde svaret — og resultatet landede som bare tool-rækker.
# ─────────────────────────────────────────────────────────────────────────────


def _transskript(history):
    with patch.object(ts, "chat_session_messages_since_last_compact", return_value=history), \
         patch("core.services.prompt_contract._get_compact_marker_for_transcript",
               return_value=None), \
         patch("core.services.prompt_contract._maybe_auto_compact_session"):
        return ts._build_structured_transcript_messages("s-appr", limit=60, include=True)


def test_afgjort_godkendelse_kommer_med_i_transskriptet():
    """Et godkendt kort må ikke forsvinde: det forklarer hvorfor tool-svaret er der."""
    history = [
        {"id": 1, "role": "user", "content": "kør kommandoen", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "assistant", "content": "Jeg venter på dit svar.", "user_id": "",
         "reasoning_content": ""},
        {"id": 3, "role": "approval_request", "content": "Godkendt: bash — ls -la",
         "user_id": "", "reasoning_content": ""},
        {"id": 4, "role": "tool", "content": "[tool_result:tool-result-abc] [bash]: fil.txt",
         "user_id": "", "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "Godkendt: bash" in tekst, "det afgjorte kort skal stå i transskriptet"
    assert "afgjort efter turen" in tekst, "det skal fremgå at afgørelsen faldt efter turen"


def test_pending_kort_skjules_stadig():
    """Et kort der IKKE er afgjort er ren UI — det skal ikke fylde i prompten."""
    history = [
        {"id": 1, "role": "user", "content": "kør", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "approval_request", "content": "Godkendelse afventer: bash — ls",
         "user_id": "", "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "Godkendelse afventer" not in tekst


def test_afvist_kort_siger_at_handlingen_ikke_skete():
    history = [
        {"id": 1, "role": "user", "content": "kør", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "approval_request", "content": "Afvist: bash — rm -rf /tmp/x",
         "user_id": "", "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "Afvist: bash" in tekst
    assert "blev ikke udført" in tekst


def test_ukendt_kortform_skjules_frem_for_at_gaettes():
    """Kan udfaldet ikke tydes, behandles det som pending — vi påstår intet."""
    history = [
        {"id": 1, "role": "user", "content": "kør", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "approval_request", "content": "et eller andet uklart",
         "user_id": "", "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "et eller andet uklart" not in tekst


def test_afgjort_kort_uden_tool_svar_skjules():
    """Et kort hvis resultat den levende tur allerede læste forklarer intet.

    Målt 22/11-2026: 12 af 19 afgjorte kort i én session havde intet tool-svar
    efter sig. At skrive dem ind ville være 12 linjer støj for nul betydning.
    """
    history = [
        {"id": 1, "role": "user", "content": "kør", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "approval_request", "content": "Godkendt: bash — ls",
         "user_id": "", "reasoning_content": ""},
        {"id": 3, "role": "assistant", "content": "Færdig.", "user_id": "",
         "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "Godkendt: bash" not in tekst


def test_kort_par_foer_tool_svar_taeller_med():
    """Kort står ofte parvis (afventer + godkendt) — parret må ikke skjule resultatet."""
    history = [
        {"id": 1, "role": "user", "content": "kør", "user_id": "", "reasoning_content": ""},
        {"id": 2, "role": "approval_request", "content": "Godkendelse afventer: bash — ls",
         "user_id": "", "reasoning_content": ""},
        {"id": 3, "role": "approval_request", "content": "Godkendt: bash — ls",
         "user_id": "", "reasoning_content": ""},
        {"id": 4, "role": "tool", "content": "[tool_result:tool-result-x] [bash]: fil.txt",
         "user_id": "", "reasoning_content": ""},
    ]
    ud = _transskript(history)
    tekst = "\n".join(str(m.get("content") or "") for m in ud)
    assert "Godkendt: bash" in tekst
    assert "Godkendelse afventer" not in tekst
