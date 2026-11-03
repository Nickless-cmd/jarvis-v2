# Centralen — forbrugs-kortlægning

**Dato:** 3. november 2026
**Kontekst:** Samtale mellem Bjørn, Jarvis og en ekstern læser (GPT) om hvorvidt Centralens
72 systemer faktisk får indflydelse på beslutninger — eller kun producerer status.
**Status:** Analyse. Intet er rettet. Alle tal er målt i denne runde medmindre andet er noteret.

---

## Sammenfatning

Tre niveauer blev skelnet:

| Niveau | Spørgsmål | Status |
|---|---|---|
| **Produceret** | Genererer systemet information? | ✅ målt — 72/72 |
| **Tilgængeligt** | Når informationen frem til et beslutningslag? | ⚠️ **ikke målt troværdigt** |
| **Virksomt** | Kan informationen ændre en beslutning? | ❌ 0 målt — og for gut-gaten *kan* den ikke |

Kernen: **flere mekanismer ser tilsluttede ud, men deres indgangsbetingelse kan intet opfylde.**
Det er samme fejlform som resten af efteråret — en mekanisme der kaldes, svarer og tæller,
men hvis svar aldrig kan ændre noget.

---

## A. `active` er et sundhedssignal, ikke et effekt-mål

`core/services/cognitive_architecture_surface.py`:

```python
active = bool(result) and (
    result.get("active", False) if isinstance(result, dict) else bool(result)
)
```

Der kontrolleres **ikke** om resultatet forbruges nogen steder.

**Konsekvens:** «72/72 aktive» betyder 72 moduler der svarer på et kald — ikke 72 der beslutter.
Tallet er korrekt som sundhedsmåling og misvisende som kapacitetsmåling.

**Skal kigges på:** om fladen skal vise to tal — `active` (svarer) og `consumed` (læses af et
beslutningslag) — så de ikke blandes sammen i én grøn række.

---

## B. Gut-gaten — seks lag af afkobling

Gaten er det eneste sted `adjusted_confidence` faktisk forbruges. Den fejler på seks måder,
og de er ordnede fra overfladisk til strukturel.

### B1. Kan matematisk ikke afvise

`derive_gut_signal` producerer kun fire mulige confidence-værdier:

| Signal | conf (med bias) | conf (uden bias) |
|---|---|---|
| proceed, ingen fejl | 0,61 | 0,50 |
| caution, mange fejl | 0,59 | 0,70 |
| caution, meget lav conf | 0,49 | 0,60 |
| proceed, mange successer | 0,91 | 0,80 |

**Domæne: 0,49–0,91. Tærskel: 0,30.** Der findes intet input der gør `would_pass` falsk.

Målt i ledgeren: `gut_gate` 558/558 grønne, `gut_gate_uden_bias` 558/558 grønne.
`mode = on`, koden er ægte, kaldet sker — og betingelsen kan ikke opfyldes.

### B2. Kender ikke opgaven

```python
# gut_engine.py:283 — preflight
signal = derive_gut_signal(task_description=task_description)

# signatur
def derive_gut_signal(*, task_description: str, confidence: float = 0.5,
                      recent_error_count: int = 0, recent_success_count: int = 0)
```

Kun `task_description` sendes. Derfor er `confidence=0.5`, `error=0`, `success=0` **altid**.
`task_description` bruges kun som tekstligt `task_hint` — den rører ikke beregningen.

Målt gennem den ægte funktion:

```
læs en fil                          conf=0.61  hunch=proceed
kritisk migration af prod-database  conf=0.61  hunch=proceed
fix en tastefejl                    conf=0.61  hunch=proceed
```

Identisk. Samme fejl i det andet kaldested, `gut_calibration.py:50`.

### B3. Kalibreringen er selvbekræftende

Kæden lukker sig selv:

1. Gaten sender ingen observationer → hunch er **altid** `proceed`
2. `_on_started` stasher `proceed` som forudsigelse
3. Runnet lykkes → `record_gut_outcome` tæller et **hit**
4. `calibration_score = hits / total`

Målt: **4292 / 4301 = 0,998**.

Det tal er ikke en kalibreret vurdering — det er **succesraten for autonome runs**.
Fordi hunch altid er `proceed`, måler kalibreringen «hvor ofte gik det godt», ikke
«hvor ofte havde maven ret». Og den ganges ind i næste confidence:
`0,5 × 0,998 + 0,111 = 0,61`.

**Maven er ikke kalibreret. Den er selvbekræftende.**

### B4. Hunch-konfidensen er inverteret

`gut_gate()` ser **kun** `confidence`. Hverken `hunch` eller retning er en parameter.

Uden bias: advarslen har **0,70**, tilladelsen **0,50**. En advarsel er per konstruktion
stærkere end en tilladelse — så med en tærskel mellem dem slipper `caution` lettere igennem
end `proceed`.

Bias-mekanismen **forstærker** fejlen når den bliver negativ:

| Bias | proceed | caution |
|---|---|---|
| +0,11 (nu) | 0,61 | 0,59 |
| −0,11 | **0,39** | **0,81** |

Så i det øjeblik maven indrømmer fejl, slipper advarslen lettere igennem.
Det er en **fortegnsfejl i semantikken**: koden behandler «hvor sikker er jeg på min retning»
som «hvor sikker er jeg på at fortsætte».

### B5. To forudsigelser — den ene kasseres

`preflight_gut_gate` beregner en hunch og **gemmer den ikke**.
`_on_started` kalder `derive_gut_signal` **igen** med `payload.get("focus")` — ikke
preflight'ens `task_description`.

To beregninger, to input, og den ene smides væk. Harmløst nu (begge er konstante),
men når observationer kobles på, evalueres en anden forudsigelse end den der lå bag starten.

### B6. Survivorship bias i målingen

`_on_started` lytter på `runtime.autonomous_run_started`. Afviser gaten et run, starter det
aldrig → intet event, ingen `_pending`, intet udfald.

Kalibreringen ser **kun de opgaver gaten allerede tillod**. Jo bedre gaten bliver til at
afvise, jo mere optimistisk bliver dens eget kalibreringstal. Det skal med i ethvert forsøgsdesign.

---

## C. Glemslen — to decay-systemer med samme navn, ingen forbindelse

Der findes **to** uafhængige decay-mekanismer:

| System | Lager | Hvad den gør |
|---|---|---|
| `forgetting_curve.py` | JSON-register via `state_store` (`_load`/`_save`) | `apply_decay_tick` hæver `decay_score`; > 0,9 → `faded` |
| `associative_recall.py` | egen tabel `recall_active_memories` | egen `_DECAY_RATE_PER_MINUTE = 0,015` |

Og en tredje, separat læser:

| `get_relevant_experiential_memories` (`db_runtime_misc.py:44`) | SQL-tabel `cognitive_experiential_memories` | filtrerer `WHERE decay_score < 0,9` |

**Målt:** `forgetting_curve` skriver til sit JSON-register. Læseren filtrerer i en SQL-tabel.
De er ikke forbundne — de hedder bare det samme.

**Konsekvens:** de 294 falmede minder har ingen konsekvens for hvad der bliver hentet.
Glemslen registrerer, den styrer ikke.

**Nuance der er vigtig:** der *findes* altså en fungerende decay-filtrering i kodebasen —
bare på en anden tabel. Det er ikke «mekanismen findes ikke», det er «mekanismen er der,
men den er ikke den samme som den der tælles i fladen». Navnekollisionen skjuler det.

---

## D. Tilgængelighed er ikke målt troværdigt

Et tidligere tal i samtalen («60 forbundet, 12 isolerede») kunne **ikke reproduceres**.
Med et bredt forbrugslag (328 filer, 6,8 MB) matcher 72/72 — fordi næsten ethvert ord
forekommer i 6,8 MB tekst.

Med et smalt, meningsfuldt mål:

| Fil | Rolle | Navne |
|---|---|---|
| `prompt_contract.py` | bygger prompten | **2 / 72** |
| `heartbeat_runtime.py` | kalder surfaces | 71 / 72 |

`heartbeat_runtime` nævner 71 fordi den *kalder* dem — det er produktion, ikke forbrug.
Prompt-byggeren nævner 2.

**Men:** grep i en fil beviser ikke at værdier ikke injiceres ad andre veje (fx gennem en
samlet blok med et andet navn). Tallet er en indikation, ikke et bevis.
**Niveau 2 er derfor stadig umålt.**

---

## Hvad der IKKE er målt

- Om en given systems *værdi* når ind i prompten (kun navnets tilstedeværelse er tjekket).
- Om der findes en opgave→værktøj-mapping et andet sted i koden.
  `pattern_strength(context)` giver ægte data pr. værktøj (`tool:bash`: 3.093 obs,
  3.000 succes, 5,9 fejl), men ingen mapping fra `task_description` til hvilke værktøjer
  den vil bruge. **Den kobling er det egentlige arbejde — ikke tærsklen.**
- Om `record_gut_outcome` nogensinde modtager andet end `proceed`.
- Om historiske kodeændringer gør at alle 4.301 observationer kan fortolkes ens.

---

## Rækkefølge — hvad der skal besluttes før der bygges

GPT's rækkefølge er rigtig. Skærpet:

1. **Definér `confidence`.** Sandsynlighed for at opgaven lykkes, eller tillid til hunch'ets
   retning? To størrelser, og koden blander dem i dag. **Denne beslutning styrer alt det følgende.**
2. **Lad samme forudsigelse følge hele vejen** fra preflight til evaluering — ikke to
   beregninger hvor den ene kasseres.
3. **Log afviste runs som afviste**, så kalibreringen ikke kun ser de tilladte (B6).
4. **Kobl situationsbestemte observationer på** — først derefter giver en tærskelændring mening.
   En højere tærskel nu ville bare afvise alle opgaver *ens*.
5. **Mål i `shadow`-mode** før det rører levende autonome opgaver.

---

## Beslutninger der kræves (ikke tekniske)

- **Ikke alle 72 bør have beslutningsmyndighed.** `existential_drift` skal kunne observere
  uden at påvirke godkendelser eller sikkerhedspolitik. Grænsen skal være **bevidst og
  dokumenteret** — ikke et biprodukt af hvad der tilfældigvis blev koblet på.
- **Fejlen er ikke at et system mangler myndighed.** Fejlen er hvis det *hævder* at påvirke
  en beslutning uden at kunne.
- **De to decay-systemer skal enten forbindes eller omdøbes**, så fladen ikke tæller en
  mekanisme der ikke er den der virker.

---

## Kilde

Alle målinger er reproduceret 3/11-2026 mod `main` @ `cce32e820`.
Gut-målingerne gennem den ægte funktion (`derive_gut_signal`, `gut_gate`, `preflight_gut_gate`),
ikke gennem en mock.
