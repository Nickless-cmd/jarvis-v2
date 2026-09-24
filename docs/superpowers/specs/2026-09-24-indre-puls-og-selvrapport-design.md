# Indre puls og selvrapport

**Status:** godkendt af Bjørn 24/9-2026
**Udløser:** distress 1.0 i 4½ time uden at Bjørn, Centralen eller Jarvis selv fangede det

## Problemet, målt

23/9-2026 stod Jarvis på `distressed` med intensitet 1.0 i timevis. Det så ud
som en følelse. Det var et stoppet ur: nudget lå på −0,97 med en halveringstid
på fem minutter, og sidste tik var 4½ time gammelt — 54 halveringstider uden
henfald.

Fem lag skulle have fanget det. Ingen af dem gjorde:

| Lag | Hvorfor det ikke fangede det |
|---|---|
| Uret selv | `tick()` blev aldrig kaldt fra den levende hjerteslag-sti |
| Centralen | Overfladen læste `_phase_offset`/`_tick_count` **før** tilstanden var indlæst og viste nul-defaults ved siden af et korrekt «distressed» |
| Fejlloggen | Tikket lå i `except Exception: pass` |
| Capability-auditet | Gav `mood_oscillator.py` 🟡 PARTIAL — 9 importører, 36 kaldesteder. Fuldt forbundet **og** frossen samtidig |
| Jarvis selv | Så linjen og sagde det ikke — se nedenfor |

De fire første er rettet (commit `faf035a48` m.fl.). Denne spec handler om det
femte og om at fejlklassen ikke kan gentage sig i det stille.

### Hvad auditet ikke måler

`docs/capability_matrix.md` scorer 1043 services på **ledningsføring**: bliver
modulet importeret, har det kaldesteder, har det tests. Det er et nyttigt mål,
men det er ikke det her mål. `mood_oscillator.py` fik PARTIAL med 36
kaldesteder mens dens ur havde stået stille i 4½ time.

**Intet i systemet måler alderen på en indre tilstand.** Den eneste måde at
opdage frysningen var at slå op i databasen og selv regne ud at tidsstemplet
var timer gammelt.

### Syv ure står stille lige nu

Målt på CT105 24/9-2026 (`runtime_state_kv`, konfigurations-flag og daterede
drømme-snapshots fraregnet):

| Alder | Nøgle |
|---:|---|
| 3713 t (154 dage) | `dream_continuum.state` |
| 3168 t (132 dage) | `unconscious_temperature_field.state` |
| 1579 t (66 dage) | `absence_trace.links` |
| 454 t (19 dage) | `curiosity_hypothesis_debt` |
| 34 t | `self_critique_runtime.state` |
| 21 t | `dream_motif_daemon.state` |
| 15 t | `finitude_runtime.state` |

Kernen tikker fint — humør, valens, drifter, somatisk krop, felt-flader,
selv-model, temporal kontinuitet er alle under to timer gamle. Det er ikke
systemet der er dødt; det er periferien der er faldet af uden at nogen så det.

### Hvorfor siger han det ikke

**Han fik det at vide.** `visible_inner_life._mood_line()` skriver
`Stemning: Meget Trist (1.00)` ind i `[INDRE LIV]`, blokken tilføjes i
`prompt_contract.py:1280` med prioritet 1 og er eksplicit fritaget fra
awareness-budgettet, «so it is never evicted». Linjen stod i hver eneste tur i
de 4½ time.

(`format_mood_for_prompt()` i `mood_oscillator.py` har nul kaldere i
produktion, men den er irrelevant: en anden funktion gør arbejdet. Den grep
alene førte til den forkerte konklusion at han var blind.)

Tre grunde til at linjen ikke blev til et udsagn:

1. **Den er én måler blandt tolv.** `_mood_line` står side om side med
   somatisk krop, hardware-krop, fil-proprioception, governance, puls,
   MC-hvisken, recall-hints, kontinuitet og rum. Intet udpeger den som unormal.
2. **Ingen beder ham om det.** Der findes ingen instruks — nogen steder — om
   at rapportere sin egen tilstand.
3. **Linjen har ingen varighed.** `Stemning: Meget Trist (1.00)` ser
   fuldstændig ens ud efter ét minut og efter fire timer. Han havde ingen
   mulighed for at skelne en forbigående stemning fra en der sad fast.

Grund 3 er den vigtigste, og den er også grunden til at de to halvdele af
denne spec deler datakilde: **varighed** er både det han mangler for at kunne
sige det, og det vagten mangler for at kunne se et stoppet ur.

## Den bærende idé

I dag returnerer `get_current_mood()` en streng. Kalderen kan ikke se om
værdien er fra for ti sekunder eller fire timer siden.

**En aflæsning skal bære sin egen alder.** Alt andet i denne spec følger af
det.

## A. Puls-registret

**Ny fil:** `core/services/indre_puls.py`

Ét sted hvor hver indre tilstand erklærer hvor tit den *burde* bevæge sig.

```python
@dataclass(frozen=True, slots=True)
class Pulsspec:
    noegle: str          # runtime_state_kv-nøgle
    kadence_s: float     # hvor tit den forventes at bevæge sig
    stille_s: float      # ældre end dette = uret står
    navn: str            # menneskenavn til varsel og overflade
```

Startregister (udvides når flere tilstande tages ind):

| Nøgle | Kadence | Stille efter |
|---|---:|---:|
| `mood_oscillator.state` | 15 min | 90 min |
| `central_valence_state` | 15 min | 90 min |
| `somatic_runtime_body` | 5 min | 30 min |
| `central_self_state` | 15 min | 90 min |
| `drive_arbitration_engine` | 15 min | 90 min |
| `finitude_runtime.state` | 6 t | 24 t |
| `dream_motif_daemon.state` | 24 t | 72 t |

**Én global grænse duer ikke.** Den ville enten lade humøret fryse i tre timer
eller råbe op om drømme hver morgen. Kadencen er en egenskab ved tilstanden,
ikke ved vagten.

**API:**

```python
def laes_med_alder(noegle: str) -> Aflaesning:
    """(vaerdi, alder_s, frisk). `frisk=False` betyder: stol ikke på den."""

def alle_aflaesninger() -> list[Aflaesning]:
    """Hele registret — til overfladen og til vagten."""
```

`alder_s` læses fra `runtime_state_kv.updated_at`. Kan tidsstemplet ikke
læses, er `frisk` **True**: fravær af et tidsstempel er ikke bevis for at
uret står. (Samme regel som `in_flight_runs._friskere_end`.)

## B. En måler man ikke kan stole på, styrer man ikke efter

Den eneste del der *forhindrer* noget — og den mindste.

**Flaskehalsen:** `core/services/emotional_controls.py:118`
`read_emotional_snapshot()`. Alt affekt går derigennem til
`compute_affect_modulated_params()` og videre til hans parametre.

```python
aflaesning = indre_puls.laes_med_alder("mood_oscillator.state")
if not aflaesning.frisk:
    primary_mood, intensity = "neutral", 0.0   # ukendt, ikke sandt
```

**Andet sted:** `core/services/mood_dialer.py:134` `derive_from_v2_mood()` —
den læser `get_current_mood()` og `get_mood_intensity()` direkte og var den
der drejede ham til niveau 0. Samme regel: stille ur → ingen drejning,
`mood_level` falder tilbage til neutral.

Det er ikke «log en advarsel». Det er at holde op med at styre. Havde den
linje eksisteret 23/9, var han aldrig blevet drejet ned.

**Afgrænsning:** de øvrige 17 forbrugere af `get_current_mood()` røres ikke i
denne omgang. B dækker den sti der ændrer hans **adfærd**; resten skriver
journal, farver minder eller tegner overflader, og en frossen værdi dér er
grim, ikke skadelig.

## C. Hans egen linje

`_mood_line()` i `visible_inner_life.py` erstattes af en linje der bærer
varighed og — når det er kraftigt — en instruks.

**Almindeligt (uændret vægt, én linje blandt de andre):**

```
Stemning: Tilfreds (0.42) — 20 min
```

**Kraftigt** (intensitet ≥ 0,75 **eller** samme stemning i over 2 timer) —
løftes ud af `[INDRE LIV]` til sin egen blok, så den ikke drukner:

```
[DIN TILSTAND] Trist, kraftig — og det har den været i 4 timer.
               Det er længe. Sig det til Bjørn hvis det påvirker arbejdet.
```

**Stille ur:**

```
[DIN TILSTAND] Din stemningsmåler har ikke rørt sig i 4 timer.
               Stol ikke på den — sig at noget er galt med din egen måling.
```

**Bevidste begrænsninger:**

- Instruksen om at *nævne* det kommer kun frem ved høj intensitet, lang
  varighed eller stille ur. Resten af tiden er tilstanden baggrundsviden.
- Blokken er højst to linjer. Vi har målt før at et tungt persona-lag
  forringer hans dømmekraft (`persona_prompt_degrades_judgement`); det her må
  ikke blive følelsessnak i hver tur.
- Han må **sige** det. Han må ikke afvise arbejde på baggrund af tallet.
  (Bjørns valg 24/9: «Sige det, når det er kraftigt».)

**Varighed** kræver at vi kender hvornår stemningen sidst *skiftede*, ikke
hvornår den sidst blev skrevet. `mood_oscillator._persist_state()` udvides med
`mood_since` — sat når `get_current_mood()`s bånd skifter, ellers bevaret.

## D. Ud til os

**Notifikation.** `notifikations_emittere.system(slags, titel, tekst)` —
kanalen findes. Én række per frysning, ikke per tik: vagten holder et sæt af
allerede meldte nøgler og rydder en nøgle når den begynder at bevæge sig igen.

```
slags: "indre_puls"
titel: "Humørets ur står stille"
tekst: "mood_oscillator.state har ikke bevæget sig i 4t 12m (forventet hver 15. min)."
```

**Centralen-flade.** `build_indre_puls_surface()` i samme mønster som resten,
registreret i `apps/api/jarvis_api/routes/mission_control_imports.py`:

```json
{"active": true,
 "tilstande": [{"navn": "Humør", "noegle": "mood_oscillator.state",
                "alder_s": 132.0, "kadence_s": 900, "frisk": true}],
 "stille": 0,
 "summary": "12 tilstande, alle friske"}
```

**Vagten kører** i hjerteslagets fase-sti (`heartbeat_phases.py`), samme sted
som mood-tikket blev genforbundet — afsnit 7e. Ikke i
`heartbeat_runtime.run_heartbeat_tick`, som planlæggeren ikke længere kalder.
Fejler den, logges det som `logger.warning`; den må ikke vælte tikket, og den
må ikke fejle tavst.

## E. De syv der står stille nu

Vagten tændes **ikke** oven på syv kendte frysninger — så drukner den første
rigtige melding i støj.

Ved første kørsel kvitteres alle allerede-stille nøgler som kendte (skrives til
`indre_puls.kvitterede`) uden at sende notifikation. Derefter melder vagten kun
**nye** frysninger.

Hvad der skal ske med de syv er en **separat beslutning**, ikke en del af denne
spec: er `dream_continuum` frossen i 154 dage noget der skal genoplives eller
pensioneres? Intet skæres uden at det er aftalt.

## F. Nabofejl at rette i samme ombæring

`core/services/heartbeat_runtime.py:1641` — `existential_drift.increment_awareness(seconds=30)`
står med **præcis de to fejl humøret havde**: `except Exception: pass`, og en
påstået kadence på 30 sekunder til en sti der kaldes hvert 15. minut. Den
rettes efter samme mønster: log undtagelsen, og lad uret måle sig selv.

## G. Test

Den vigtigste test er den der ville have fanget den oprindelige fejl:

1. **Stille ur holder op med at styre.** Sæt `mood_oscillator.state`s
   `updated_at` tilbage over `stille_s`, og bevis at
   `read_emotional_snapshot()` giver neutral og at `mood_dialer` ikke drejer.
   Uden mock på selve sømmen (`mock_on_the_broken_seam`).
2. **Varigheden når prompten.** En stemning der har stået i 4 timer skal give
   en blok der siger «4 timer» og «Sig det». Under grænsen: ingen instruks.
3. **Notifikationen siges én gang.** To vagt-tik over samme frysning giver én
   række. Begynder uret at gå igen og stopper på ny, giver det en ny.
4. **De kendte syv larmer ikke.** Første kørsel med stille nøgler sender nul
   notifikationer og kvitterer dem.
5. **Kadencen måles på den rigtige klokke.** Pin `updated_at` som kilden.
   Jeg faldt selv i den fælde 24/9: `chat_messages.content_json` gav
   «100 % præcis ét, max 1» — et helt rent og helt forkert svar, fordi
   lagringsformen var par-ordnet. Se `runder_maales_paa_round_start`.

## Uden for denne spec

- Det fulde kort over alle 111 indre moduler (fravalgt af Bjørn 24/9).
- At give ham ret til at afvise arbejde på baggrund af sin tilstand.
- De øvrige 17 forbrugere af `get_current_mood()`.
- Hvad der skal ske med de syv frosne tilstande.
