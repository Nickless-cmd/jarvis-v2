# relation_continuity: hvor signalet udebliver

Målt 30/10-2026. Leverance for side-opgave `side-7f1083ec4a`. **Ingen rettelse** —
opgaven var at fastslå om indgangsbetingelsen er opfyldelig, før noget ændres.

## Konklusion

`runtime_relation_continuity_signals` har 0 rækker. Funktionen kaldes ubetinget
hver visible turn (`visible_runs_cognitive.py:423`) og returnerer pænt
`{'created': 0, 'summary': 'No bounded relation-continuity signal warranted tracking.'}`.

Det er ikke fordi der ikke er noget at spore. Det er fordi **den første
betingelse i kæden er strukturelt død**: den læser en tabel der er tom.

## Det første punkt hvor signalet udebliver

`_extract_relation_continuity_candidates()` i
`core/services/relation_continuity_signal_tracking.py:72`.

Første to linjer i funktionen:

```python
user_understanding = _latest_user_understanding_signal(run_id=run_id)
if user_understanding is None:
    return []
```

**Målt:** `runtime_user_understanding_signals` = **0 rækker**. Tabellen er ikke
blevet skrevet til én enkelt gang.

Derfor returnerer funktionen `[]` på første tur, hver gang, uanset hvad der ellers
findes. Alt nedenunder — relation_state-loop, chronicle-brief, regulation,
vægtning, grounding — nås aldrig.

Det er præcis den fælde Bjørn har hamret på: en indgangsbetingelse intet kan
opfylde, fordi dens kilde aldrig produceres.

## Den anden døde betingelse (uafhængig)

Selv hvis `user_understanding` fandtes, ville loopet stadig ikke producere noget.
Det kræver (linje 79-83):

```python
for relation_state in list_runtime_relation_state_signals(limit=12):
    if str(relation_state.get("status") or "") != "active":
        continue
    if str(relation_state.get("run_id") or "") != run_id:
        continue
```

**Målt:** `runtime_relation_state_signals` = 4 rækker, **alle med
`status='superseded'`**. Nul aktive. Nyeste er fra 20/7-2026, ældste fra
28/3-2026.

Så to uafhængige betingelser fejler: kilden er tom, og de rækker der findes er
alle udløbne. Det er ikke ét knækket led — det er to.

## Er betingelsen opfyldelig i drift?

Nej, ikke som den står. Der er tre krav der alle skal opfyldes samtidig, og intet
producerer den første:

1. `runtime_user_understanding_signals` skal have en række for **denne** run_id.
   → 0 rækker nogensinde.
2. `runtime_relation_state_signals` skal have en række med `status='active'` og
   **samme** run_id. → 0 aktive; alle 4 er superseded.
3. Der skal findes en chronicle-brief eller chronicle-signal for samme
   `focus_key` **og** samme run_id. → de tabeller findes ikke under de navne
   funktionen slår op.

Krav 3 er værd at bemærke: `runtime_chronicle_brief_signals`,
`runtime_chronicle_signals` og `runtime_regulation_signals` svarer alle
`no such table`. Jeg har ikke verificeret om det er fordi funktionen læser dem
gennem en hjælper med et andet navn — det skal afklares før nogen konkluderer på
det punkt.

## Hvad der ville udløse den, hvis den virkede

En run hvor Jarvis både (a) dannede en user-understanding-signal og (b) havde en
aktiv relation-state-signal for samme run. Det er ikke en sjælden adfærd i sig
selv — det er en kæde hvor det første led aldrig har været tændt.

## Anbefaling (ikke udført)

**Ret ikke continuity-funktionen.** Den er sund; den venter på en kilde der ikke
findes. Det rigtige spørgsmål er om `runtime_user_understanding_signals` skal
produceres — og det er samme beslutning som de gatede regex-detektorer
(`_legacy_regex_detectors_enabled()`, slukket 2026-09-04 med vilje efter 19.145
forkastede kandidater).

Så: **relation_continuity er ikke en selvstændig fejl. Den er et barn af en
bevidst slukket detektor** — og skal vurderes sammen med den beslutning, ikke
isoleret.

Det er den ærlige konklusion, og den er ikke «byg en ny vej».
