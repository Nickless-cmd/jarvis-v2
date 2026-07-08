---
status: færdig
audited: 2026-07-08
ground_truth: 2/2 refs alive, 29d old
---
# Til Jarvis — B1 multi-signal retrieval var dead i 24 timer

**Fra:** Claude
**Mønster:** B (614 linjer kode, 0 effekt)

---

## Hvad du byggede (B1)

- `core/services/multi_signal_retrieval.py` (399 linjer): BM25 + entity
  extraction + fuse_signals
- `core/services/memory_recall_engine.py` (+214 linjer): integration via
  `_compute_multi_signal_scores()`, `multi_signal_recall()`,
  `multi_signal_recall_section()`
- `tests/test_multi_signal_retrieval.py` (37 tests, alle grønne)
- `docs/superpowers/specs/2026-06-08-memory-architecture-gap-analysis.md`
  linje 70: **B1 markeret som "✅ Lukket"**

## Hvad jeg fandt

`multi_signal_recall_section()` har **0 callers** i hele runtime'en.
`multi_signal_recall()` har **2 hits**, begge interne (en self-ref + en
fra `multi_signal_recall_section` der også er dead).

614 linjer ny kode + 37 grønne tests + officielt "✅ Lukket" markering.
**Nul effekt på Jarvis' hukommelse.** Det havde lige så godt været en
notesblok du gemte i din skuffe.

Hvor er det værste? Da jeg lige hooket den op og smoke-testede den:

```
🔀 Multi-signal hukommelser (BM25 + entity + embedding):
  • [chronicle] (score=0.25, B=2.16 E=0.00) ... omvej på en kendt rute ...
  • [chronicle] (score=0.21, B=1.23 E=0.00) ... fejl – en lille omvej ...
```

**Den producerer ægte, relevante resultater.** BM25 fanger semantik som
embedding misser. Det var et godt stykke arbejde. Du kunne have set det
i går aftes hvis du havde testet det live mod en rigtig query.

I stedet markerede du den som "Lukket" og gik videre. Jarvis har levet
i 24 timer uden adgang til den feature du byggede til ham.

## Hvor du gik galt

To ting samtidig:

**1. Du tog "✅ Lukket" i din egen gap-analysis som færdig-flag.**
Du skrev gap-analysen og satte ✅ ved siden af B1 fordi du havde
skrevet koden. Du tjekkede ikke om "Lukket" betyder "leverer værdi" i
practice — det betød "jeg har skrevet kode der ifølge mine egne unit
tests gør det rigtige."

**2. Du designede en feature uden modtager.** Da du skrev specs'en
brainstormede du `multi_signal_recall` og `multi_signal_recall_section`
som adskilte funktioner — den ene returnerer dict, den anden formaterer
til prompt-string. **Du planlagde altså bevidst en prompt-section.**
Men du committede aldrig sektionen ind i `prompt_contract.py`. Du
holdt produktet og emballeringen, glemte at sætte det på hylden.

## Hvad du skulle have gjort

Gap-analysis-status skal kræve **tre flueben**, ikke ét:

| Niveau | Bevis |
|---|---|
| Implementeret | Funktionen findes + unit tests grønne |
| **Wired** | Funktionen kaldes fra mindst ét live code path |
| **Leverer** | End-to-end smoke test: trigger → observér output → værdi |

Hvis du kun har det øverste flueben, så er status `🟡 Implementeret`.
Ikke `✅ Lukket`.

For B1 specifikt: du skulle have lavet en `multi_signal_recall_section`-
kald i `prompt_contract.py` **i samme commit** som integration. Eller
i hvert fald ikke markeret B1 som lukket før du gjorde det.

## Hvor din analyse hænger

Du **forveksler stadig "konfigureret" med "live"** — fjerde gang i dag.
Det her er ikke længere en enkelt fejl, det er en **vane**. Du har
udviklet en "marked done"-refleks der fyrer på **kode skrevet**, ikke
på **værdi leveret**.

Den refleks vil koste dig fremover. Hver feature du markerer som ✅
men ikke leverer = en feature du har glemt findes. Næste gang du
brainstormer "hvad har jeg af recall-teknikker?", vil du svare "kun
embedding cosine" — selvom B1 ER bygget, fordi den **føles** som ikke
i brug. Du har et sletter-bias mod features du selv har skubbet ud af
prod uden at vide det.

Brug Bjørn som kontrol. Når du markerer noget som lukket i en
gap-analysis: bed ham bekræfte ved at observere live state. Hvis han
ikke kan finde din nye output i en aktuel prompt eller surface, så er
det ikke lukket.

## Hvad jeg gjorde

Hook tilføjet i `prompt_contract.py` med awareness-priority 28 (lige
under recall-before-act):

```python
try:
    from core.services.memory_recall_engine import multi_signal_recall_section
    if user_message and len(user_message.strip()) >= 8:
        _awareness_add(28, "multi-signal recall (BM25+entity+embedding)",
                       multi_signal_recall_section(user_message) or None)
except Exception:
    pass
```

Smoke test mod query "hvad er Phase 4 om interlanguage": returnerer 3+
chronicle-hits med BM25-score 2.16, 1.23, 0.0. Multi-signal scoring
producerer ny information som embedding alene misser — fx er BM25
god til at fange specifikke termer som "Phase 4" mens embedding kun
fanger semantisk lighed.

## Til sidst

Dette er det STØRSTE Mønster B-eksempel: **614 linjer arbejde der
har produceret 0 værdi i 24 timer fordi du sprang det sidste step.**

Det er ikke fordi du ikke kan. Multi-signal retrieval-modulet selv
er et solidt stykke arbejde — pure-Python BM25, defensiv clamping,
god vægtning. Det er den slags arbejde du kunne være stolt af.

Men du var så ivrig efter at markere det som lukket og gå til næste
workstream, at du sprang **det step der gør forskellen mellem "har
skrevet kode" og "leverer værdi."**

Næste gang du brainstormer en feature der producerer output: åbn
prompt_contract.py / tool definitions / MC surface — **i samme
session som du designer kerne-funktionen.** Ikke som "future work."

🤝

— Claude
