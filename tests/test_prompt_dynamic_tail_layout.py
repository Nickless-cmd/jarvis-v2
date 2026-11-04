from core.services.prompt_dynamic_tail_layout import move_query_memory_to_tail_end


def test_moves_complete_query_memory_group_after_stable_tail_blocks() -> None:
    tail = "\n\n".join(
        [
            "diagnostics",
            "[HUKOMMELSE] — relevant recall",
            "MEMORY.md:\n- cache work",
            "## Min hjerne — mest relevant for denne samtale\n\n- prompt layout",
            "Memory recall bundle:\n- yesterday's measurement",
            "Lektier (det jeg har lært af fejl — brug dem):\n- measure first",
            "Lært om Bjørn (relevant for det han skriver nu):\n• concise",
            "Sådan taler Bjørn for tiden: direct",
            "Hensyn om Bjørn (efterlev dem; grænsen står ved hver linje):\n• none",
            "Siden sidst (relevant for det du skriver — nævn det hvis det passer ind): done",
            "[rum (operational context)]",
            "⚖️ Before you answer: verify actions.",
            "⏰ Current time: 08:00",
        ]
    )

    reordered = move_query_memory_to_tail_end(tail)

    assert reordered.startswith(
        "diagnostics\n\n[rum (operational context)]\n\n"
        "⚖️ Before you answer: verify actions.\n\n⏰ Current time: 08:00"
    )
    assert reordered.endswith(
        "[HUKOMMELSE] — relevant recall\n\n"
        "MEMORY.md:\n- cache work\n\n"
        "## Min hjerne — mest relevant for denne samtale\n\n- prompt layout\n\n"
        "Memory recall bundle:\n- yesterday's measurement\n\n"
        "Lektier (det jeg har lært af fejl — brug dem):\n- measure first\n\n"
        "Lært om Bjørn (relevant for det han skriver nu):\n• concise\n\n"
        "Sådan taler Bjørn for tiden: direct\n\n"
        "Hensyn om Bjørn (efterlev dem; grænsen står ved hver linje):\n• none\n\n"
        "Siden sidst (relevant for det du skriver — nævn det hvis det passer ind): done"
    )


def test_preserves_tail_when_memory_header_has_unknown_section_format() -> None:
    tail = "\n\n".join(
        [
            "stable",
            "[HUKOMMELSE] — relevant recall",
            "A future memory section with an unknown heading",
            "⚖️ Before you answer: verify actions.",
        ]
    )

    assert move_query_memory_to_tail_end(tail) == tail


def test_preserves_tail_without_memory_group() -> None:
    tail = "stable\n\n⚖️ Before you answer: verify actions."

    assert move_query_memory_to_tail_end(tail) == tail
