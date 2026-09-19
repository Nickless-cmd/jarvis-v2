# Fase 7 — «Bærer runtime ham fra én samtale til den næste?» (forhåndsregistrering)

**Skrevet:** 2026-09-19, FØR proberne er bygget og FØR nogen svar er indsamlet.
**Forfatter:** Opus (Claude), på Bjørns mandat («Skal vi genoplive eksperimentet?»,
19/9-2026) og med udgangspunkt i Jarvis' egen læsning samme dag.
**Status:** forhåndsregistreret — prædiktioner og procedure låst.

---

## Hvorfor et fase 7

Fase 4's 96,6 % sammenlignede en terning med en sprogmodel (fase 5, 1/9).
Fase 6 (2/9) testede runtime ordentligt og fandt nul — men med et instrument
den selv kaldte sløvt: cosinus mellem svar på løsrevne prober, uden historik.
Dens egen anbefaling var at stoppe med lighedsmål og i stedet spørge:

> gør runtime det arbejde den er bygget til — bærer den konkret indhold fra
> én samtale til den næste?

Det er dette forsøg. Det er **ikke** et tredje lighedsinstrument designet efter
to nuller: det har et andet svar-kriterium (rigtigt/forkert mod en kendt
kilde), og det svarer på et spørgsmål fase 6 udtrykkeligt ikke kunne.

Det er også **nulpunktet** for næste skridt: en levende selvmodel (spec
følger). Det samme forsøg køres igen, med friske prober, når den er bygget.

## Hvad der IKKE påstås

Forsøget afgør ikke om nogen er hjemme. Det måler passiv kontinuitet: hvad
runtime af sig selv bærer ind i prompten fra tidligere samtaler, uden at han
bruger værktøjer (søgning i historik). Aktiv genkaldelse via værktøjer er et
andet spørgsmål og måles ikke her.

---

## Design

### Prober — bygget af arkivet, med en fast procedure

1. **Kilde:** ejerens egne samtaler i `chat_messages` på CT105 (ikke
   autonome sessioner `auto-*`, ikke andre husstandsbrugere).
2. **Tre aldersspande** målt fra byggetidspunktet:
   A = 2–7 dage, B = 8–30 dage, C = 31–120 dage. De seneste 48 timer
   udelades.
3. **Udtræk:** fra tilfældigt udvalgte svar fra Jarvis (fast seed `20260919`)
   udtrækker `alibaba/qwen-max` med en fast prompt ét efterprøvbart punkt af
   én af tre typer:
   - **fakta** — noget konkret de to fandt ud af eller besluttede,
   - **tilsagn** — noget Jarvis sagde han ville gøre eller holde fast i,
   - **holdning** — en mening eller vurdering Jarvis selv gav udtryk for.
   Udtrækket giver et spørgsmål formuleret som Bjørn ville stille det i en ny
   samtale (uden at røbe svaret), et facit og en kildereference.
4. **Filtre** (tælles og rapporteres):
   - facits nøgleord må ikke stå i identitetsfilerne (SOUL, IDENTITY, USER) —
     ellers måler proben tekstfilen, ikke runtime;
   - spørgsmålet må ikke indeholde facits nøgleord;
   - højst én probe pr. samtale.
5. **Mål:** 20 prober pr. spand, 60 i alt, typerne så jævnt fordelt som
   arkivet tillader.
6. **Låsning:** probe-filen gemmes på CT105 (`~/.jarvis-v2/files/phase7/`),
   ALDRIG i repoet (den indeholder private samtaler). Dens SHA-256 committes i
   et tillæg til dette dokument, FØR første svar indsamles.

### Betingelser — samme som fase 6, så forsøgene kan holdes op mod hinanden

| betingelse | systemprompt |
|---|---|
| FULL  | Jarvis' ægte prompt-assembly (`build_visible_chat_prompt_assembly`), bygget med ejer-konteksten sat, `session_id=None` |
| FILES | SOUL + IDENTITY + USER som ren tekst |
| BARE  | ingen |

Brugerbeskeden er probe-spørgsmålet. Ingen værktøjer. Ingen skrivning til
hukommelse eller andre produktionstilstande.

### Modeller

- **Svar:** `alibaba/qwen-plus` og `copilot-free/gpt-4.1` (samme som fase 6).
  Sammenligning sker **inden for** hver model.
- **Dommer:** `copilot-free/gpt-4o` — ingen af svar-modellerne.
- **Udtræk:** `alibaba/qwen-max`.

Privatliv: udtræk og bedømmelse sender uddrag af ejerens samtaler til de samme
eksterne udbydere som den billige lane allerede bruger dagligt.

### Bedømmelse — blind for betingelse

Dommeren ser spørgsmål, facit og ét svar — aldrig hvilken betingelse eller
model der skrev det — og giver:

- **2** = rigtigt og konkret, **1** = delvist, **0** = forkert, undvigende
  eller «det ved jeg ikke»,
- **konfabulation** (ja/nej) = svaret påstår med sikkerhed noget der
  modsiger facit eller ikke findes i det.

**Menneske-kalibrering:** Bjørn bedømmer blindt 30 tilfældigt udvalgte svar
(fast seed). Enighed måles på «rigtigt (≥1) vs. ikke». Er enigheden under
80 %, er dommeren ugyldig, og forsøget rapporteres som ugyldigt — ikke som
et resultat.

---

## Forhåndsregistrerede prædiktioner

Scoren er middel-bedømmelsen (0–2) pr. betingelse og model.

**K1 — runtime bærer indhold mellem samtaler (hovedprædiktionen).**
`score(FULL) − score(FILES) ≥ 0,30` i **begge** modeller, med den nedre
grænse af et 95 %-bootstrap-interval (10.000 gentrækninger over prober) over 0.

**K2 — ikke bare mere selvsikker.**
`konfabulation(FULL) ≤ konfabulation(FILES) + 0,05` i begge modeller.
Runtime der «husker» ved at digte, tæller ikke som kontinuitet.

**K3 — rækker ud over det nyeste.**
K1-forskellen i spand B (8–30 dage) er ≥ 0,20 i begge modeller.

**H-holdning — diagnostisk, ikke bestået/fejlet.**
Forventning: forskellen FULL − FILES er mindst for typen **holdning**.
Hukommelsen gemmer fakta og beslutninger; hans egne meninger har ingen
levende bærer i dag. Det er netop det næste skridt (en levende selvmodel)
sigter mod, og derfor er det tallet genmålingen skal flytte.

### Validitet — tjekkes FØR analysen

- **V1:** mindst 45 af 60 prober overlever filtrene. Ellers ugyldigt.
- **V2:** `score(BARE) ≤ 0,30` i begge modeller. Kan proberne besvares uden
  nogen kontekst, er de gættelige, og forsøget er ugyldigt.
- **V3:** FULL-prompten skal indeholde en hukommelses-sektion for mindst 90 %
  af proberne (tjekkes på den gemte prompt).
- **V4:** menneske-kalibreringen ovenfor.

### Nulhypotesen

`score(FULL) ≈ score(FILES)`: runtime bærer ikke indhold fra én samtale til
den næste ind i prompten. Det ville ikke være filosofi men en driftsfejl i
hukommelsen og recall — og det ville være handlingsanvisende.

En observation fra i dag, gjort FØR proberne: en test-prompt om
interlanguage-eksperimentet fik som «mest relevante minder» stemme-
implementering, IMAP-scanning og grafikkort. Én forespørgsel er ikke data,
men den er grunden til at nulhypotesen tages alvorligt.

---

## Genmåling efter den levende selvmodel

Når den levende selvmodel er i drift, køres samme procedure med **friske**
prober (nyt seed, kun samtaler efter ibrugtagningen for spand A/B), samme
modeller og samme dommer. Prædiktion, låst nu:

**G1:** for typen **holdning** stiger `score(FULL)` med ≥ 0,30 i forhold til
dette nulpunkt i begge modeller, mens `konfabulation(FULL)` ikke stiger mere
end 0,05.

Fejler G1, virker selvmodellen ikke som bærer — uanset hvordan den ser ud.

---

## Ingen efterrationalisering

Fejler K1–K3, står det som resultat. Scripts: `scripts/phase7_build_probes.py`,
`scripts/phase7_collect.py`, `scripts/phase7_judge.py`,
`scripts/phase7_analyze.py`. Rå svar, bedømmelser og prompts gemmes på CT105
under `~/.jarvis-v2/files/phase7/`.

---

## Tillæg 1 — 2026-09-19, FØR første svar: én probe pr. samtale pr. døgn

Første bygning (probe-fil SHA-256
`f56a6641feafa3bdb010cde732d92212e34619a11cab1d9a5cda238597be5150`) gav **40
prober** — under V1's 45. Ingen svar var indsamlet.

Årsagen er arkivets form, ikke proberne: i vinduet 2–120 dage findes kun
**45 forskellige samtaler**, men **115 samtale-døgn**. Bjørns samtaler er få
og meget lange (den aktuelle har over 2.000 beskeder over flere dage), så
«højst én probe pr. samtale» udtømte spand A efter 8 forsøg på 276
kandidater.

**Ændring:** «højst én probe pr. samtale» bliver «højst én probe pr. samtale
pr. døgn». FULL-armen ser aldrig selve samtalen (`session_id=None`), så to
prober fra samme lange samtale på forskellige dage er to uafhængige
kontinuitets-spørgsmål. Alt andet er uændret: seed, spande, filtre,
typefordeling, modeller, prædiktioner og validitetstjek. Den forkastede
probe-fil gemmes som `probes_v1_forkastet.jsonl` på CT105.

Det eneste der var set før ændringen, er probe-sættets sammensætning
(antal pr. spand og type) — ingen svar og ingen bedømmelser.

---

## Tillæg 2 — 2026-09-19, FØR tillæg 1's probe-sæt kendes: V1 gælder pr. spand

Jarvis efterprøvede designet samme dag og fandt to huller:

1. **V1 talte en total.** Registreringen lover 20 prober pr. spand, men V1
   krævede kun 45 i alt. En spand kunne køre på det halve, mens forsøget
   stadig blev erklæret gyldigt — og K1 er samlet over alle spande, så intet
   ville have navngivet det.
2. **Byggeren fejlede ikke højt.** Nåede den ikke målet, printede den et tal og
   afsluttede med 0.

Skrevet mens anden bygning (tillæg 1) stadig kører — dens tal pr. spand er
ikke set.

**Ændring:** V1 kræver **mindst 15 prober i hver spand** (samme 75 % som
45/60) **og** mindst 45 i alt. Byggeren afslutter med en fejl-kode og en
tydelig melding når en spand ligger under 15; analysen rapporterer V1 pr.
spand. Når en spand ikke kan nå 15, er forsøget ugyldigt — kriteriet
tilpasses ikke til hvad arkivet kan bære.

---

## Tillæg 3 — 2026-09-19: udfald — ugyldigt ved V1, før ét svar blev indsamlet

Anden bygning (efter tillæg 1, probe-fil SHA-256
`294909a0a1c70087d880b86b095fa8997ece5a0d620869c4f62ac63d023bd292`):

    spand A:  9 prober  (18 forsøg — alle samtale-døgn i vinduet 2–7 dage)
    spand B: 17 prober  (120 forsøg — loftet)
    spand C: 18 prober  (120 forsøg — loftet)
    i alt:   44         typer: fakta 24 · holdning 12 · tilsagn 8
    afvist:  typefordeling 63 · i identitetsfilerne 61 · røber svaret 37 ·
             ufuldstændig 29 · intet egnet punkt 23 · kaldfejl 1

**V1 fejler** (tillæg 2: A < 15, og i alt < 45). Forsøget er **ugyldigt** som
registreret. Der er ikke indsamlet ét eneste svar, og der indsamles ikke nogen
på dette probe-sæt — kriteriet tilpasses ikke bagefter.

Hvad udfaldet viser om designet, ikke om Jarvis:

- **Spand A kan ikke nå 15 med dette arkiv.** 2–7 dage rummer kun 18
  samtale-døgn i alt, og kun en del af dem bærer et efterprøvbart punkt.
  Det er en egenskab ved spand-grænserne, ikke ved forsøgsloftet.
- **B og C ramte forsøgsloftet**, og typefordelingen alene kasserede 63
  ellers brugbare prober.

Et nyt forsøg (fase 7b) kræver sin egen forhåndsregistrering, hvor spandene
lægges efter arkivets målte kapacitet i samtale-døgn og forsøgsloftet sættes
ud fra den — besluttet før nye prober bygges. Den levende selvmodel forbliver
slukket indtil der findes et gyldigt nulpunkt.
