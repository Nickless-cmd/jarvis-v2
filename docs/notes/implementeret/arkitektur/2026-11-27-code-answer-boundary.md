# Code mode: explicit answer boundary and terminal merge

Status: implementeret

## Problem

The live answer could be reclassified as work after later tools, leaving only
the last synthesis visible. Character count could fold a long synthesis early
or a short answer late.

## Beslutning

Date: 2026-11-27. Owner: visible runtime / code transcript presentation.
Classification: **same-version**, additive optional fields in existing
`chat_messages.content_json` text blocks; no schema migration or new state file.

The model declares presentation intent with `[[jarvis:answer]]` at the start
of a line before closing prose. This starts an answer, not a turn completion,
approval, or tool restriction. Later tools and syntheses remain legal.
`visible_run_wire.explicit_answer_stream` consumes the declaration incrementally
and emits one `answer_start` SSE event before the first answer word. Token-split
markers cannot leak; quoted, inline, and fenced examples are ordinary content.
The existing accumulator retains the declaration until canonical block assembly,
where the same scanner converts its exact location into metadata. No answer
length heuristic is used to reconstruct the code boundary.

New text blocks carry `code_answer_protocol: 1`; exactly one answer block carries
`code_answer_start: true`. Persisted blocks also record `code_answer_source` as
`explicit` or `terminal`. The API normalizer and stream reducer preserve the
fields. Under protocol 1, code mode ignores legacy `phase=final_answer` guesses.
If a model omits the declaration, a terminal fallback marks the final text block,
and the relay logs `code-answer-start: TERMINAL_FALLBACK`. This is deliberately
late rather than a guessed early fold. The relay's existing length heuristic is
retained for legacy/chat clients; it is not authoritative for code mode.

## Overvejede alternativer

Changing the length threshold cannot distinguish short answers from long
commentary. Reclassifying at persistence creates a second answer boundary.
Waiting for every model round to finish would delay all answer streaming.
The explicit declaration keeps streaming and presentation intent separate.

## Konsekvenser

Old rows are not rewritten. A new client reading old blocks without protocol
metadata retains the legacy phase/position fallback. Old clients ignore the
additional fields. Chat rendering and runtime governance are not redefined by
the code protocol.

Code presentation projects the pacing cursor before revealing later work.
The head folds at the first displayed answer word, independently of the pacing
clock. After server completion AND paced-text completion, only late work rows
fade/collapse over the fold duration. Answer and synthesis containers remain
mounted and visually join as intervening work disappears. Late work remains
available in the head. The live-to-saved handover waits for the exit animation.

Verification: parser chunk-boundary/quotation/fence tests; producer → relay →
accumulator integration; normalization/reducer/pacing presentation tests; real
Chromium geometry probe `apps/jarvis-desk/src/harness/verify-code-fold.py`.


Production follow-up (2026-11-27): run
`visible-fab32668ab3d43c3b3af8b026bf60eec` omitted the declaration. Its 1,794-character
closing answer preceded `suggest_next_task`, and only the 260-character tail
received the terminal boundary. Inspection of the actual prompt selector found
that `output_discipline` is supplied but has no section budget, so its marker
instruction never reaches the assembled prompt. The code-only presentation
instruction now lives near the start of the mandatory code contract, retained
in its compact form, and in the V2 current-turn recency anchor. A regression
passes the real mode orientation through the real budget selector and assembles
the dynamic tail for V1/V2 and full/compact profiles; chat gets no code marker
instruction. This fixes instruction delivery; actual model compliance still
requires observing an explicit declaration on a subsequent production turn.
