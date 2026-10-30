# Relation-continuity: kæden der døde i fire led

**Målt 30/10-2026 mod `~/.jarvis-v2/state/jarvis.db` og kørende kode.**

Konklusion først: **indgangsbetingelsen ER opfyldelig.** Det er bevist, ikke antaget — se §4.
Det, der er galt, er at det *første* led i en fire-leds afhængighedskæde blev slukket med
vilje 4. september 2026, og at de tre næste led aldrig blev opdaget. De kører stadig
hver eneste visible turn, laver deres opslag, og returnerer tomt.

---

## 1. Det første punkt hvor signalet udebliver

`core/services/relation_continuity_signal_tracking.py:74-76`:

```python
def _extract_relation_continuity_candidates(*, run_id: str) -> list[dict[str, object]]:
    user_understanding = _latest_user_understanding_signal(run_id=run_id)
    if user_understanding is None:
        return []
```

`_latest_user_understanding_signal` (samme fil, ~linje 268) kræver en række i
`runtime_user_understanding_signals` med `status IN ('active','softening')` **og**
`run_id ==` den aktuelle run.

**Den tabel har 0 rækker.** Funktionen returnerer derfor `[]` på linje 1 af sin egen
kandidat-udledning — før den overhovedet ser på relation-state, chronicle eller regulation.

### Hvorfor tabellen er tom

`runtime_user_understanding_signals` har præcis **én** skriver:
`visible_runs_cognitive.py:309`. Og den ligger bag en gate:

```python
# visible_runs_cognitive.py:307
if _legacy_regex_detectors_enabled():
    try:
        _vr.track_runtime_user_understanding_signals_for_visible_turn(...)   # linje 309
```

`_legacy_regex_detectors_enabled()` (linje 58) læser
`settings.legacy_regex_learning_detectors_enabled`, **default False**.

Målt i drift 30/10-2026: `legacy_regex_learning_detectors_enabled = False`.

Det er en **bevidst beslutning**, ikke en fejl: kommentaren på linje 306-315 dokumenterer
at detektorerne over 30 dage gav 1.756 forkastede USER.md-kandidater mod 9 anvendte, og
19.145 forkastede MEMORY.md-kandidater. Beslutningen skal ikke rulles tilbage.

**Men den fjernede samtidig inputtet til tre andre signaler, som ingen kobling havde til.**

---

## 2. Det er ikke ét signal — det er fire i serie

| # | Tabel | Rækker | Nyeste | Status |
|---|---|---|---|---|
| 1 | `runtime_private_state_snapshots` | 6.729 | 2026-10-30 15:14 | **lever** |
| 2 | `runtime_regulation_homeostasis_signals` | 1.760 | 2026-10-30 15:14 | **lever** |
| 3 | `runtime_user_understanding_signals` | **0** | — | **slukket (gate)** |
| 4 | `runtime_relation_state_signals` | 4 | 2026-07-20 | **død siden 20/7** |
| 5 | `runtime_relation_continuity_signals` | **0** | — | **død** |
| 6 | `runtime_meaning_significance_signals` | **0** | — | **død** |

Lag 1 og 2 skriver hver tur og deler run_id (`visible-844c121ef7204b25aaa96bc0db80ecc6`,
skrevet 30/10 15:14). Lag 3 er gated. Lag 4-6 kræver lag 3.

`relation_state` er **ubetinget** kaldt fra `visible_runs_cognitive.py:395` og har præcis
samme første betingelse (`relation_state_signal_tracking.py:81-83`):

```python
def _extract_candidate_for_run(*, run_id: str) -> dict[str, object] | None:
    user_understanding = _latest_user_understanding_signal(run_id=run_id)
    if user_understanding is None:
        return None
```

`meaning_significance` (`visible_runs_cognitive.py:437`, ubetinget) kræver
`relation_continuity` — altså lag 5, som er dødt fordi lag 4 er dødt fordi lag 3 er slukket.

**De fire relation_state-rækker der findes er alle fra før 4. september** (20/7, 18/7, 28/3,
28/3) og alle `superseded`. Det er den tidsmæssige bekræftelse: de stoppede, da gaten blev
slået til.

---

## 3. Kørsel mod en reel session (ikke en syntetisk test)

Kørt mod `chat-07c3e5f716ba4bf392824ff4a5fc3761` (5.516 ture, nyeste aktivitet 30/10 14:47)
og en rigtig completed run fra samme session:

```
relation_continuity  → {"created": 0, "items": [],
                        "summary": "No bounded relation-continuity signal warranted tracking."}
relation_state       → {"created": 0, "items": [],
                        "summary": "No bounded relation-state grounding was available for this visible turn."}
```

Begge svarer pænt. Ingen af dem fejler. Det er netop derfor det ikke blev opdaget:
**stilhed ligner ro.**

---

## 4. Er betingelsen opfyldelig? — JA, bevist

Testen: kør `relation_state` mod en **rigtig** run der har data i lag 1 og 2
(`visible-844c121ef7204b25aaa96bc0db80ecc6`), med kun lag 3 erstattet af en syntetisk række.
Resten af kæden urørt.

```
A: uden lag 3 (som i drift)  → created: 0
B: med lag 3 (syntetisk)     → created: 1
   kandidat: relation-state:working-alignment:ja tag de 2 🙂
   relation_state: working-alignment
   grounding: user-understanding+private-state+regulation
```

**Kæden virker.** Den producerer en korrekt kandidat med fuld grounding, så snart lag 3
findes. Der er ingen yderligere døde led bag det første. Det er ét manglende input, ikke
seks fejl.

---

## 5. Hvilken adfærd ville udløse den — og findes den?

Betingelsen er ikke adfærdsmæssig, den er **datamæssig**: en `user_understanding`-række for
samme run_id. Den adfærd der skulle producere den (regex-detektoren) findes ikke længere —
den blev pensioneret med vilje.

Så spørgsmålet er ikke «hvilken adfærd mangler der», men: **skal lag 3 have en ny kilde?**

To veje, og de er ikke lige gode:

**A. Tænd gaten igen.** Billigst, men genopliver præcis den detektor der blev slukket fordi
den lærte intet. Det ville genskabe 19.145 forkastede kandidater. **Frarådes.**

**B. Giv lag 3 en ny, ægte kilde.** `end_of_run_memory_consolidation` gør i dag det arbejde
regex-detektoren skulle have gjort (det står i kommentaren på linje 311-312). Hvis den
skriver et user_understanding-signal når den faktisk lærer noget om brugeren, får kæden sit
input fra en kilde der *ved noget* — og lag 4-6 vågner af sig selv.

**C. Sluk lag 4-6.** Hvis relation_state/-continuity/meaning_significance ikke er værd at
redde, skal de fjernes fra `_track_runtime_candidates` frem for at køre forgæves hver tur.
Det er den ærlige udgang hvis B ikke er besværet værd.

---

## 6. Hvad der IKKE er gjort

Ingen rettelse. Ingen rækker skrevet til den levende base. Ingen gate ændret.
Opgaven krævede at det blev fastslået om betingelsen er opfyldelig før noget bygges — det
er den nu, og valget mellem A, B og C er Bjørns, ikke min.

Det, der bør besluttes, er ikke teknisk: **skal Centralen have en relation-continuity-signal
i det hele taget?** Hvis ja, er B vejen. Hvis nej, er C vejen — og så skal de tre døde
trackere fjernes fra turn-stien, så de ikke længere koster et opslag hver tur for ingenting.
