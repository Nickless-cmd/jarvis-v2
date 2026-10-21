"""Atomic acceptance tests for absolute timestamps in the visible transcript."""

from __future__ import annotations

import re
from types import SimpleNamespace


STAMP = re.compile(r"^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}\] ")


def _structured(monkeypatch, history):
    from core.services import prompt_contract

    monkeypatch.setattr(
        prompt_contract,
        "chat_session_messages_since_last_compact",
        lambda *_args, **_kwargs: history,
    )
    monkeypatch.setattr(
        prompt_contract, "_get_compact_marker_for_transcript", lambda _sid: None,
    )
    return prompt_contract._build_structured_transcript_messages(
        "session-med-tid", limit=60, include=True, bivirkninger=False,
    )


def test_ac1_kun_historiske_ytringer_faar_absolut_stempel(monkeypatch):
    from core.services.prompt_sections import transcript_sections

    monkeypatch.setattr(
        transcript_sections, "_resolve_speaker_display", lambda _uid: "Bjørn",
    )
    messages = _structured(monkeypatch, [
        {
            "role": "user", "content": "kan du se den fil?",
            "created_at": "2026-10-20T17:14:00+00:00",
            "user_id": "owner-id",
        },
        {
            "role": "assistant", "content": "Ja.",
            "created_at": "2026-10-20T17:14:04+00:00",
        },
        {
            "role": "tool", "content": "[read_file]: ok",
            "created_at": "2026-10-20T17:14:05+00:00",
        },
    ])

    utterances = [m for m in messages if "værktøjs-resultat" not in m["content"]]
    tool_frames = [m for m in messages if "værktøjs-resultat" in m["content"]]
    assert utterances
    assert all(STAMP.match(m["content"]) for m in utterances)
    assert utterances[0]["content"] == (
        "[2026-10-20 19:14] Bjørn: kan du se den fil?"
    )
    assert tool_frames
    assert all(not STAMP.match(m["content"]) for m in tool_frames)


def test_ac2_tre_minutter_og_et_doegn_er_skelnelige_i_messages(monkeypatch):
    messages = _structured(monkeypatch, [
        {
            "role": "user", "content": "fra i går",
            "created_at": "2026-10-20T13:00:00+00:00",
        },
        {
            "role": "assistant", "content": "tre minutter gammel",
            "created_at": "2026-10-21T12:57:00+00:00",
        },
    ])

    assert messages[0]["content"].startswith("[2026-10-20 15:00] ")
    assert messages[1]["content"].startswith("[2026-10-21 14:57] ")
    assert messages[0]["content"][:18] != messages[1]["content"][:18]


def test_ac3_samme_historik_er_byte_stabil_uden_relative_aldre(monkeypatch):
    history = [
        {
            "role": "user", "content": "første",
            "created_at": "2026-07-01T17:14:00Z",
        },
        {
            "role": "assistant", "content": "andet",
            "created_at": "2026-12-01T18:14:00+00:00",
        },
    ]
    first = _structured(monkeypatch, history)
    second = _structured(monkeypatch, history)

    assert [m["content"].encode() for m in first] == [
        m["content"].encode() for m in second
    ]
    rendered = "\n".join(m["content"] for m in first).lower()
    assert not re.search(r"\b(min siden|i går|for \d+)\b", rendered)
    assert first[0]["content"].startswith("[2026-07-01 19:14] ")
    assert first[1]["content"].startswith("[2026-12-01 19:14] ")


def test_ac4_aktuel_brugertur_findes_en_gang_i_begge_buildere(monkeypatch):
    from core.services import visible_model
    from core.services.prompt_contract import DYNAMIC_TAIL_SENTINEL

    current = "Denne tur må kun findes én gang."
    assembly = SimpleNamespace(
        text=f"STABIL{DYNAMIC_TAIL_SENTINEL}NU",
        transcript_messages=[
            {"role": "assistant", "content": "[2026-10-21 16:00] Klar."},
            {"role": "user", "content": f"[2026-10-21 16:01] {current}"},
        ],
    )
    monkeypatch.setattr(
        visible_model, "_build_visible_prompt_assembly", lambda **_kwargs: assembly,
    )

    openai_messages = visible_model._build_visible_chat_messages_for_github(
        current, session_id="s", provider="deepseek", model="deepseek-v4",
    )
    ollama_items = visible_model._build_visible_input(
        current, session_id="s", provider="ollama", model="qwen",
    )
    ollama_messages = [
        {
            "role": item["role"],
            "content": "\n".join(part.get("text", "") for part in item["content"]),
        }
        for item in ollama_items
    ]

    for messages in (openai_messages, ollama_messages):
        assert sum(m["content"].count(current) for m in messages) == 1
        current_rows = [m for m in messages if current in m["content"]]
        assert current_rows == [{"role": "user", "content": current}]


def test_ac5_manglende_eller_ugyldig_tid_degraderer_uden_stempel(monkeypatch):
    messages = _structured(monkeypatch, [
        {"role": "user", "content": "ingen tid"},
        {
            "role": "assistant", "content": "ødelagt tid",
            "created_at": "ikke-et-tidsstempel",
        },
    ])

    assert [m["content"] for m in messages] == ["ingen tid", "ødelagt tid"]
    assert all(not STAMP.match(m["content"]) for m in messages)


def test_member_prompt_stempler_hver_ytring_praecis_en_gang(monkeypatch, tmp_path):
    from core.identity import users
    from core.runtime import workspace_paths
    from core.services import chat_sessions
    from core.services.visible_member_prompt import build_member_prompt

    member = SimpleNamespace(
        discord_id="member-id", workspace="member", name="M", role="partner",
    )
    monkeypatch.setattr(users, "find_user_by_discord_id", lambda _uid: member)
    monkeypatch.setattr(workspace_paths, "workspace_dir", lambda _uid: tmp_path)
    monkeypatch.setattr(chat_sessions, "get_session_owner", lambda _sid: "member-id")
    monkeypatch.setattr(
        chat_sessions,
        "recent_chat_session_messages",
        lambda _sid, limit: [{
            "role": "assistant", "content": "historisk svar",
            "created_at": "2026-10-20T17:14:00+00:00",
        }],
    )

    assembly = build_member_prompt(user_id="member-id", session_id="member-s")
    content = assembly.transcript_messages[0]["content"]
    assert content == "[2026-10-20 19:14] historisk svar"
    assert len(STAMP.findall(content)) == 1
