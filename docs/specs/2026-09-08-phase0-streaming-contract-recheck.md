# Phase 0 — genmåling af streaming-kontrakten

Dato: 2026-09-08 · Hører til [DeepSeek Harness Lessons for Jarvis-v2](2026-09-08-deepseek-harness-lessons-for-jarvis.md)

Fase 0 kræver karakteriseringstests for otte forløb. Før man skriver dem, bør
man vide hvad der allerede er dækket — og `docs/streaming-production-grade-spec.md`
er både opført som evidens i harness-spec'en og indeholder en navngiven
hul-liste (H1–H6) med `fil:linje`-henvisninger.

Den er genmålt i dag. **Alle seks huller er lukkede eller overhalede, og
dokumentets linjehenvisninger opløser sig ikke længere.**

## H1 — «`_subscribe` opgiver efter ~24 s stilhed: bart `break`» → LUKKET

`chat_stream_v2.py:518` bærer nu kommentaren *«H1/G6: aldrig bare break — emit
syntetisk terminal-frame så klienten forlader 'working', + fyr
subscriber_timeout-nerve.»* Nerven er ikke længere død kode.

## H2 — «followup: intet retry, ét `urlopen`» → LUKKET

`visible_followup.py` har nu tyve forekomster af retry/forsøg og en
`agentic_round_retry_enabled()`-port — altså rund-niveau-retry, som spec'ens
egen §4.1 foreskrev.

## H3 — «ollama inter-byte-frys ubundet» → OVERHALET

Der findes nu et selvstændigt modul, `core/services/visible_runs_watchdog.py`,
med et **tavsheds-loft** der fanger stallede streams uden at dræbe lange runder.
Beskyttelsen er bredere end den H3 efterlyste.

## H4 — «provider-fejl uden `observe`» → LUKKET

`core/services/visible_model_observe.py` findes som eget modul.

## H5 — «`_persist_session_assistant_message` i `except: pass`» → LUKKET PÅ 8 AF 9

Otte af ni kaldsteder er ikke længere slugt. Det ene tilbageværende (linje 5737)
persisterer afbrydelses-noten, og dér er slugningen forsvarlig: en høflighedsbesked
under en afbrydelse må ikke kunne gøre afbrydelsen til et krak.

## H6 — «frame-drop ved 4000-cap» → LUKKET

`run_event_log.py:30`: `_MAX_FRAMES = 4000` er nu et **ring-buffer-vindue**, ikke
en hård cap, med en kommentar der navngiver symptomet det rettede
(*«klipper gerne midt i runde 5»*).

## Den egentlige lære: linjenumre rådner

Spec'ens H3 og H4 peger på `visible_model.py:1621`, `:1387`, `:1124`. Filen er i
dag **783 linjer**. Den er splittet i otte moduler — `visible_model_ollama.py`,
`_sse.py`, `_observe.py`, `_prompt.py`, `_adapters.py`, `_types.py` m.fl. — så
ingen af de tre henvisninger kan slås op.

Det er samme fejlklasse som CLAUDE.md's fil-liste, der pegede på `db.py` med
33.056 linjer da filen havde 1.213. **Et dokument der citerer linjenumre bliver
usandt af at koden bliver bedre.**

Konsekvens for harness-spec'en: den fører
`docs/streaming-production-grade-spec.md` som evidens for nuværende tilstand.
Det er den ikke længere. Fase 2 («stream settlement, retry, outcomes») skal
bygge på en genmålt kontrakt, ikke på H-listen.

## Hvad det betyder for karakteriseringstestene

Fire af de otte forløb har allerede levende værn med navngivne moduler bag sig
— terminal-frame ved stilhed, rund-retry, watchdog, ring-buffer. De skal
karakteriseres som **eksisterende adfærd der ikke må gå tabt**, ikke som huller
der skal lukkes.

De forløb der stadig mangler et entydigt værn:

- afbrud **før** første delta (ingen overflade-besked må opstå)
- afbrud **efter** delta (den nøjagtige leverede prefix skal ankres)
- lokal-tool-disconnect: `aborted_before_dispatch` vs. `outcome_unknown` —
  ingen af de 97 subprocess-kaldsteder kan i dag skelne

Det er de tre, testene skal starte med.
