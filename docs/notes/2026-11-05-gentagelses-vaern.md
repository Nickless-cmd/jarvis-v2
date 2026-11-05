---
status: bygget
slags: funktion
fravalg:
  - "Endnu en sætning i prompten (batch-instruks, rundebudget-varsel): målt tre gange 5/11, ingen flyttede adfærd"
  - "Tvungen tool_choice=required i nudge-runden: (c) tie er et legitimt svar, og et tvunget kald ville gøre det umuligt"
  - "Embedding-lighed: tung, og kan ikke adskille «samme ord» fra «ny information»; shingle/Jaccard er allerede i huset"
  - "Ny shingle/Jaccard-kode: importeret fra sensory_perception_bridge i stedet for duplikeret"
  - "Nyt runtime-flag i settings.py: hollow_promise_guard_enabled bruger runtime-state, så samme mønster er fulgt"
---

Status: implementeret

# Gentagelses-værn

## Problem

Jarvis gentager sig selv uden at noget er ændret (Bjørn 5/11-2026: «din
gentagelser uden ændring er en anden sag»). Instruktioner i prompten flyttede
ikke adfærd. Hollow-promise-vagten gør — 299 indgreb — fordi den læser outputtet
i stedet for at bede om en ændring.

## Beslutning

`core/services/repetition_guard.py` med samme kontrakt som hollow_promise_guard:

- `is_repetition(final_text, previous_texts, ...)`: Jaccard over 3-ords-shingles
  (`_shingle`/`_jaccard` importeret fra `sensory_perception_bridge`), tærskel 0,8,
  de seneste 5 svar. Konservativ: under 12 ord, tomt, fejl → False. Ny
  information (tal, filnavne, commit-hashes som ingen tidligere svar har) → False
  uanset lighed.
- `REPETITION_NUDGE`: siger at svaret gentager, og kræver (a) ændr tilstand,
  (b) eskalér tydeligt, eller (c) tie.
- `should_nudge(final_text, session_id)`: produktionsindgangen (flag + sessionens
  seneste assistent-svar + `is_repetition`).
- Flag `repetition_guard_enabled`, default TRUE, env `JARVIS_REPETITION_GUARD`.
- Koblet i `visible_runs.py` lige efter hollow-promise-blokken: nudge lægges via
  `_tur_hale.tilfoej_naeste`, én runde mere, loft `_repetition_nudges < 1` pr. run,
  fail-open.

`tests/test_repetition_guard.py` måler også selve `visible_runs.py` (AST): fjernes
kaldet, nudgen eller loftet, fejler testen. Mutationskørt 5/11: fjernet kald → 2
røde, fjernet nudge → 1 rød.

## Overvejede alternativer

Se `fravalg` i frontmatter. Kort: prompt-sætninger (virker ikke), tvungen
tool_choice (udelukker «tie»), embeddings (for tung, blind for fakta), duplikeret
shingle-kode (to sandheder).

## Konsekvenser

- Ét ekstra kald i en tur der gentager sig; intet ved normale ture.
- Falsk positiv-risiko er bevidst lav (høj tærskel, ny-information-undtagelse);
  en misset gentagelse koster en sætning, en falsk positiv bryder en tur.
- Hvis svaret er kort («Ja.») måles der ikke, så korte gentagelser slipper igennem.
- `core/runtime/settings.py` er ikke rørt: flaget følger hollow-promise-mønstret
  (env + runtime-state), ikke settings.
- Noten ligger fladt som opgaven angav; `verify_notes.py` tjekker kun den nye
  mappeform (`implementeret/funktion/`), så flyt den dertil hvis den skal tælle.
