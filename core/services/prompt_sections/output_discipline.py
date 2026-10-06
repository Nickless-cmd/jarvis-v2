"""Output discipline guidance for visible model prompts."""


def _output_discipline_instruction(*, strength: str) -> str:
    """Return the output guidance appropriate to a model's strength."""
    lines = [
        "Output discipline:",
        "- After each tool result, consider: do I have enough to answer? If yes, synthesize your",
        "  findings and respond directly — do not keep calling tools when you already have the answer.",
        "- Finish your sentence with punctuation before a tool call — never cut off mid-word.",
        "- Tool results are for you — refer to them in your own words, never reproduce them verbatim.",
        "- Before finishing code work, account for concrete unresolved findings: fix relevant new test failures now; for a deferred coverage gap call flag_side_task with finding_kind, disposition, path, behavior and evidence. Never remove a failed test and silently claim the behavior is verified.",
        # Maalt 6/10-2026: **0 af 10.774** assistent-beskeder har et
        # mermaid-hegn. (Et foerste opslag gav 3 — de var en compact_marker og
        # to tool-resultater; jeg havde glemt at filtrere paa rolle.)
        #
        # RETTELSE til min egen begrundelse: jeg skrev at rendereren «har
        # eksisteret siden foraaret». Den var SLETTET 29/9 af Codex
        # (`93be59bb6`: «wiring them would alter settled HTML»). Jeg laeste
        # MermaidBlock.tsx fra mit eget checkout, som stod paa en gammel gren
        # med ukommitterede aendringer — ikke fra main. Da linjen her gik live,
        # var den altsaa FALSK.
        #
        # Jarvis gjorde den sand: han laeste den, fandt ingen renderer, og byggede
        # en ny med et streaming-vaern der respekterer netop det krav Codex
        # slettede den gamle for at beskytte (`c78754043`).
        "- A ```mermaid fenced block is RENDERED as a diagram in jarvis-desk. Reach for it when a",
        "  relationship, flow or sequence IS the answer — it beats describing boxes and arrows in prose.",
        "  On mobile it currently shows as readable source, so always put the conclusion in text too.",
        # `vis_graf` er pinned i state/tool_tags.pinned.json. Filens eget _doc
        # siger reglen: et vaerktoej den STAAENDE prompt beder om SKAL staa der,
        # ellers skriver prompten en anvisning vaerktoejssaettet ikke kan
        # indfri. Routeren sender 70-97 af 494 vaerktoejer, og et nyt uden
        # kald-historik kommer ikke i always-core af sig selv.
        "- For numbers — a trend, a comparison, a before/after — call vis_graf. It draws a chart",
        "  that renders inline in BOTH desk and the phone. You pass data; the server draws it.",
        "  Say the conclusion in words as well: the chart carries the shape, not the point.",
    ]
    if str(strength) == "strong":
        lines += [
            "- Go straight to the point. Try the simplest approach first without going in circles. Do not overdo it.",
            "- Keep text between tool calls to ≤25 words. Keep final responses to ≤100 words unless the task genuinely requires more.",
            # Uden denne linje slaar de to instruktioner hinanden ihjel: et
            # diagram er altid over 100 ord, saa ordloftet ville i praksis
            # forbyde det han lige fik at vide at han kunne.
            "- A diagram or code fence does NOT count toward the word cap — the cap is about prose.",
        ]
    return "\n".join(lines)
