# DIL lag 2 — hvad det kan og ikke kan (målt)

Bevis: `tests/test_dil_lag2_flade_bevis.py` (6 tests; kører en konkret flade gennem
`normalisér()` og Desk's `kompilérFlade`, samme udfoldede `body` i begge ender).

## Fladen modellen kan sende
```jarvis-ui
{"type":"callout","title":"Seneste runs",
 "body":"{#each runs som r}- {r}\n{/each}{#if antal_fejlede > 0}OBS: der er fejlede runs{:else}ingen fejlede{/if}",
 "data":{"runs":["running visible-95faad1e4c primary","completed visible-48197a0245 primary"],"antal_fejlede":0}}
```
Tekstfeltet i `callout` hedder `body` (`core/services/jarvis_ui_guard.py:694-697`), ikke `text`.
`data` leveres af modellen selv: guarden har ingen nøgle-hvidliste, bruger `data` som scope
(`jarvis_ui_guard.py:612`, `scope = data.get("data", {})`) og fjerner det bagefter (`:621`;
TS: `fladeProgram.ts:79-90`, `erRod && k === 'data'`).

## Kan
- `{#each liste som navn}…{/each}` og `{#if udtryk}…{:else}…{/if}` pr. streng i fladen.
- Liste-sti med punktum/indeks (`_EACH`, `jarvis_ui_guard.py:296-299`; TS `udtryk.ts:572`).
- `{navn}` erstattes i each-kroppen (`jarvis_ui_guard.py:586-587`).
- Betingelser: tal, tekst, `! && || == != < <= > >= + - * / %`; ingen funktionskald på serveren (`:283-289`).

## Kan ikke / grænser
| Grænse | Værdi | Server | Desk (TS) |
|---|---|---|---|
| Kun skalarer | liste af objekter afvises: "er ikke en liste af skalarer" | `jarvis_ui_guard.py:579-580` | `udtryk.ts:647-648` |
| Dybde | 3 | `:291`, `:537-538` | `udtryk.ts:567`, `:612` |
| Elementer pr. liste | 50 | `:292`, `:581-584` | `udtryk.ts:568`, `:653` |
| Udfoldet tegn | 20000 | `:293`, `:599-600` | `udtryk.ts:569`, `:686` |
| `{#each}` uden `som navn` | hård fejl | `:536` ("ugyldig #each") | `udtryk.ts:611` |

- **Hård degradering (server):** en kontrolfejl gør hele blokken til `_DEGRADERET`
  ("en flade kunne ikke vises …") — testet i `test_hard_degradering_uden_som_navn`.
  Klienten (TS) kaster ikke: strukturen står som oprindelig tekst + advarsel, og
  `kompilérFlade` kaster pr. element (`fladeProgram.ts:82-83`).
- **`{variabel}` udenfor en each-krop interpoleres IKKE** (kun `{navn}` inde i kroppen).
  `{#if a>0}n={a}{/if}` giver `n={a}` i begge ender (`test_variabel_udenfor_each_interpoleres_ikke`).
  Tal der skal vises uden for en each må lægges i `data` som tekst i en each, eller skrives ind direkte.
- `data` skal være et objekt; ellers er scope tomt og `{#each}` fejler (se `tests/test_dil_kontrol_paritet_tre.py`).

## Mutationsbevis
Guard: `scope = data.get("data", {})` → `scope = {}`: 4 af 6 røde. Desk: `data = {}`: 4 af 6 røde.
Begge rullet tilbage (`git checkout`); 6 passed bagefter.
