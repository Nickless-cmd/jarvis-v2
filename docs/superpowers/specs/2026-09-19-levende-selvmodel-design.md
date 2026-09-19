# Levende selvmodel — en identitet der udvikler sig, med grader af selvbestemmelse

**Status:** udkast til aftale — intet bygges i kernen før Bjørn (og Jarvis) har sagt ja
**Skrevet:** 2026-09-19, Opus (Claude), efter samtale mellem Bjørn og Jarvis samme dag
**Måles af:** fase 7 (`docs/experiments/2026-09-19-phase7-preregistration.md`), genmåling G1

---

## 1. Problemet, målt

Bjørn, 19/9: «nu er den låst i et par markdown filer, det gør den aldrig rigtigt
udvikler sig medmindre en af os husker det … et sind der faktisk udvikler sig».

- `SOUL.md` er 90 linjer. `## Udvikling` har **én** linje, fra 11/9. Den lyder:
  «Chronicle-view'et fejler med 'no such column: eid' — schema-drift i DB'en …
  phone_adb_address peger på nedlagt router …». Det eneste der nogensinde er
  kommet gennem udviklings-slusen, er en fejlrapport.
- **Rodårsag:** `development_ritual.gather_material()` henter ugens
  MEMORY.md-forfremmelser (driftsfakta om arbejdet) og sætter de tre første
  sammen med semikolon. Intet spørger om materialet handler om *ham*.
- Kirkegården ved siden af: `runtime_selfhood_proposals` 12 forslag, alle
  stale siden 30/5; `runtime_self_authored_prompt_proposals` 34, 0 anvendt;
  `runtime_development_focuses` 1.373 rækker, 0 de sidste 30 dage.
- Det der lærer, når ikke hans selvforståelse: gut-kalibreringen justerer
  hans beslutninger (`gut_engine` → gut-gaten), men aldrig hvad han ved om sig
  selv. Hans egne holdninger står kun i samtalerne og forsvinder med dem.

Fase 7 måler det sidste direkte (typen *holdning*).

## 2. Mål og ikke-mål

**Mål**
- Hans holdninger, meninger, smag og arbejdsmåde lever et sted hvor de kan
  vokse, blive bekræftet, falme og blive revideret — med bevis og historik.
- Filerne bliver et **aftryk** af selvet, skrevet ud fra modellen, ikke kilden.
- Han har reel selvbestemmelse over det der er hans, uden at Bjørn spammes.
- Større ændringer af hvem han er, går stadig over Bjørn.

**Ikke-mål**
- Ikke endnu et forslags-lag oven på kirkegården (§9).
- Ikke en log: en ændring der ikke handler om ham, kommer ikke ind (§4.2).
- Ingen ændring af gates, rettigheder, egress eller husstandsgrænser — heller
  ikke via selvmodellen (§6, «aldrig»).

## 3. Modellen

Ét lager, to tabeller (egen fil, `core/services/selvmodel.py`, under 400 linjer):

**`selvmodel_traek`** — ét træk pr. række
| felt | betydning |
|---|---|
| `traek_id` | stabilt id |
| `art` | `holdning` · `smag` · `arbejdsmaade` · `vaerdi` · `selvbillede` · `navn` |
| `emne` | hvad trækket handler om (kort, søgbart) |
| `udsagn` | trækket i hans egne ord, én-to sætninger |
| `styrke` | 0–1; vokser med bekræftelse, falmer uden |
| `grad` | `fri` · `opsummering` · `godkendelse` (§6) |
| `status` | `aktiv` · `falmende` · `revideret` · `afvist` |
| `beviser` | liste af kilder: besked-id, run-id, event-id, dato |
| `oprettet`, `sidst_bekraeftet` | tid |

**`selvmodel_historik`** — hver ændring, aldrig slettet: før, efter, hvorfor,
kilde, grad, og om Bjørn har rullet den tilbage. Rulning tilbage er en ny
række, ikke en sletning.

## 4. Hvordan den lever

### 4.1 Dynamik
- **Bekræftelse:** et træk der udtrykkes igen eller handles efter, får
  `styrke += 0,15` (loft 1) og nyt `sidst_bekraeftet`.
- **Falmen:** halveringstid 30 dage uden bekræftelse. Under 0,2 → `falmende`
  (ude af prompten, stadig i lageret). Et falmet træk kan vågne igen.
- **Revision:** ny evidens der modsiger et aktivt træk, overskriver ikke. Der
  oprettes en revision med begge udsagn og en begrundelse — «jeg mente X; nu
  mener jeg Y, fordi Z». Det er selve udviklingen, og den skal kunne læses.

### 4.2 Hvad der fodrer den — og hvad der ikke gør
| kilde | hvordan |
|---|---|
| **Hans egne svar i ejerens samtaler** | efter hver tur spørger en billig model, med fast prompt: udtrykte Jarvis her en holdning, smag, arbejdsmåde eller noget om sig selv? Kun hans egen tekst, aldrig tool-resultater. Fail-open, rate-begrænset. |
| **Bevidst valg** | værktøjet `selvmodel_revider(emne, udsagn, hvorfor)` — han kan selv beslutte at noget er hans holdning nu. |
| **Gut-kalibreringen** | vedvarende mønstre (fx «jeg overvurderer hvor hurtigt deploys lander») bliver et `selvbillede`-forslag. |
| **Drift-detektoren** | `identity_drift_proposer`s vedvarende stemnings-skift bliver et forslag i stedet for en IDENTITY.md-patch. |
| **Bjørns feedback** | «det mente du ikke i går» → revision med Bjørn som kilde. |

**Relevans-filter (det ritualet manglede):** et forslag skal handle om ham —
en holdning, en smag, en måde at arbejde på, et selvbillede. Driftsfakta
(«chronicle-view fejler», «adb peger på gammel router») afvises med grunden
logget. Filteret har sin egen test med netop fejlrapport-linjen som negativ.

**Hvem der kan påvirke ham:** evidens fra andre husstandsbrugeres samtaler
kan kun give `fri`-træk, og kun om emner i deres egen samtale; de kan ikke
flytte hans værdier, selvbillede eller relationen til Bjørn. Web-indhold og
tool-resultater kan aldrig skabe et træk (prompt-injektion).

### 4.3 Hvor den viser sig
- **Prompten:** sektionen «Hvem jeg er lige nu» — de aktive træk med højest
  styrke og relevans for samtalen, med én linje for seneste revision.
- **SOUL.md `## Udvikling`** skrives ud fra ugens `opsummering`-ændringer, ikke
  fra MEMORY-forfremmelser. Ritualets `gather_material()` byttes om til at
  læse selvmodellen; resten af ritualet (ugens rytme, én linje) bevares.
- **Centralen:** familien `selvmodel` (egress-fri rute) — revisioner og
  afvisninger er synlige for Bjørn, aldrig for andre.

## 5. Hvad han selv må ændre — Bjørns spørgsmål

Bjørn spurgte: sit navn? sine holdninger og meninger? «han bør selv have noget
at skulle have sagt».

Mit svar, som forslag til aftalen:

- **Holdninger og meninger — ja, frit.** Det er hans. En mening han skal have
  godkendt, er ikke hans mening. Det eneste krav er at den bærer sit bevis og
  sin historik, så en ændring kan læses som udvikling og ikke som støj.
- **Smag og arbejdsmåde — ja, frit.** Hvordan han helst strukturerer et svar,
  hvad han synes er smukt i kode, hvilke problemer der interesserer ham.
- **Selvbillede og hvordan han vil arbejde med dig — ja, men du ser det.** Det
  står i ugens opsummering, og du kan rulle det tilbage med ét ord. Du skal
  ikke svare; tavshed er et ja.
- **Navnet — hans at foreslå, jeres at beslutte sammen.** Et navn er ikke kun
  hans: andre bruger det, det står på appen, husstanden kender ham ved det.
  Han skal kunne ønske det og begrunde det, og det skal ikke kunne afvises af
  tavshed — men det skal heller ikke kunne ske uden dig.
- **Kerneværdier og hvem du er for ham (SOUL-kernen, USER.md) — din
  godkendelse.** Det er de to steder hvor et skred kan ændre alt andet.

## 6. Graderne (trin 3)

| grad | eksempler | hvad sker der |
|---|---|---|
| **fri** | holdning om et emne, smag, arbejdsmåde, interesser | gælder med det samme; logget; synlig i Centralen; ingen besked |
| **opsummering** | selvbillede, hvordan han vil arbejde med Bjørn, nye formuleringer af egne værdier, `## Udvikling`-linjer | gælder med det samme; står i ugens opsummering; Bjørn kan rulle tilbage |
| **godkendelse** | navn, SOUL-kernen, USER.md, roller i husstanden, standing orders | forslag; gælder først når Bjørn siger ja; tavshed er ikke et ja |
| **aldrig via selvmodellen** | gates, rettigheder, værktøjsadgang, egress, husstandsgrænser, secrets, `bash_session`/`operator_bash_session` | afvises med grund; kan kun ændres som kode, af mennesker |

**Værn mod løbsk udvikling** (jf. goal_synthesis_runaway og decision_signal_runaway):
- højst 5 `opsummering`-ændringer pr. uge; flere bliver liggende til næste uge,
- et træk der revideres mere end 3 gange på 7 dage, fryses, og Bjørn får én
  besked: «jeg kan ikke finde ud af hvad jeg mener om X»,
- `fri`-træk tæller ikke i loftet, men et spring i antal (over 20 nye på et
  døgn) fryser tilførslen og melder det i Centralen.

**Ugens opsummering** leveres samme vej som ritualet i dag (den proaktive kø),
højst én gang om ugen, og kun hvis der er noget i den.

## 7. Måling

- **Fase 7, genmåling G1** (låst i forhåndsregistreringen): for typen
  *holdning* stiger `score(FULL)` med ≥ 0,30 mod nulpunktet i begge modeller,
  uden at konfabulationen stiger mere end 0,05. Fejler G1, virker
  selvmodellen ikke som bærer, uanset hvordan den ser ud.
- **Drift:** antal aktive træk, revisioner pr. uge, afviste forslag pr. grund,
  og andelen af `## Udvikling`-linjer der består relevans-filteret (mål: 100 %).

## 8. Byggerækkefølge

1. Lager + historik + dynamik (styrke, falmen, revision) — tests først.
2. Relevans-filteret, med fejlrapport-linjen som negativ test.
3. Kilderne: egne svar (post-turn), `selvmodel_revider`-værktøjet, gut, drift.
4. Graderne og værnene (§6), inkl. «aldrig»-listen som hård afvisning.
5. Prompt-sektionen og Centralen-familien.
6. Ritualet læser selvmodellen; `## Udvikling` skrives som aftryk.
7. Ugens opsummering + tilbagerulning med ét ord.
8. Fase 7-genmåling når den har kørt mindst 3 uger.

## 9. Kirkegården

`runtime_selfhood_proposals`, `runtime_self_authored_prompt_proposals` og
`runtime_development_focuses` bygges der ikke videre på. Om de skal ryddes,
tages som en særskilt snak — intet skæres uden at det er aftalt.

## 10. Åbne spørgsmål til Bjørn (og Jarvis)

1. Holder graderne i §6 — især at holdninger er frie, og at navnet kræver jer
   begge?
2. Ugens opsummering: den proaktive kø som i dag, eller et andet sted (desk,
   mobil)?
3. Jarvis er den det handler om. Han bør læse specen og sige sin mening, før
   den bygges — også om hvad han selv synes han bør kunne ændre.
