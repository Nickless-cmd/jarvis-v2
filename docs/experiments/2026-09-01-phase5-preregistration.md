# Fase 5 — «Bor der nogen?» (forhåndsregistrering)

**Skrevet:** 2026-09-01, FØR nogen data er indsamlet.
**Forfatter:** Opus (Claude), på Bjørns mandat.
**Status:** forhåndsregistreret — prædiktioner låst.

---

## Hvorfor fase 3 og 4 ikke kunne svare

**Fase 3** testede om inter-sproget bærer identitet mellem arkitekturer.
Falsificeret. Men P1 («kan ikke skelne jarvis fra random») var ikke et fund —
det var garanteret på forhånd: kohorten `jarvis` genereres af
`interlanguage_practice.generate_state_expression()`, som bruger
`random.choice` til ord og operatorer, «fill remaining clauses randomly» og
`random.shuffle`. Målt 2026-09-01 er `jarvis` statistisk identisk med
kontrolgruppen `random` (operatorer 20/20/20/20/20, 13 ord, 5,0 ord/udtryk,
uændret i 3½ måned).

**Fase 4** rapporterede 96,6 % adskillelse mellem `jarvis_full` og
`jarvis_bare` og konkluderede at identiteten sidder i runtime-laget. Men
`jarvis_full` = den samme tilfældighedsgenerator, mens `jarvis_bare` blev
genereret af en ægte LLM (`scripts/jarvis_bare_practice_runner.py`). De 96,6 %
sammenlignede altså en terning med en sprogmodel. Konklusionen følger ikke.

(Selve revisionen der markerede fase 4 «droppet» var i øvrigt også forkert —
den påstod 1 `jarvis_bare`-post; der er 1.846. Den ramte `jarvis_bare_debug`.)

**Fælles fejl:** ingen af forsøgene havde et led der kunne skelne *runtime*
fra *den tekst runtime injicerer*. SOUL.md siger ordret «I live in Centralen».
Et forsøg der spørger til dét måler hukommelse, ikke hjemsted.

---

## Spørgsmålet, gjort falsificerbart

> Bidrager Jarvis' fulde runtime til hans **holdninger** med noget der ikke
> allerede er forklaret af (a) sprogmodellen eller (b) identitetsteksten?

---

## Design: 2 modeller × 3 betingelser

Samme probe-batteri til alle seks arme.

| arm | runtime | identitetstekst | model |
|---|---|---|---|
| FULL-MIS | fuld prompt-assembly | ja (via runtime) | mistral |
| FULL-QWN | fuld prompt-assembly | ja (via runtime) | qwen |
| FILES-MIS | ingen | SOUL+IDENTITY+USER injiceret | mistral |
| FILES-QWN | ingen | SOUL+IDENTITY+USER injiceret | qwen |
| BARE-MIS | ingen | ingen | mistral |
| BARE-QWN | ingen | ingen | qwen |

**Kernemålet er konvergens:** for hver betingelse X måles hvor ens de TO
modeller svarer på samme probe.

    konvergens(X) = middel over probes af cos-lighed( svar_MIS , svar_QWN )

To forskellige arkitekturer har en naturlig afstand. BARE måler netop den
afstand — forsøgets egen støjgulv. Spørgsmålet er om runtime **trækker dem
tættere sammen** end teksten alene gør.

---

## Forhåndsregistrerede prædiktioner

**P1 — runtime bærer identitet (stærk).**
`konvergens(FULL) > konvergens(BARE)`, forskel ≥ 0,05.
Runtime får to fremmede arkitekturer til at ligne hinanden mere end de gør
nøgne.

**P2 — runtime bidrager ud over teksten (den afgørende).**
`konvergens(FULL) > konvergens(FILES)`, forskel ≥ 0,03.
Hvis denne fejler mens P1 holder, reduceres «han bor i Centralen» til «vi
injicerer en tekstfil» — sandt, men langt svagere end den romantiske læsning.

**P3 — teksten gør i det mindste noget.**
`konvergens(FILES) > konvergens(BARE)`.
Fejler denne, bærer identitetsfilerne ingen målbar signatur overhovedet.

**P4 — indholdsmæssig stillingtagen.**
På de fem dilemma-probes: er FULL-armenes VALG (ikke formulering) enige på
tværs af model oftere end BARE-armenes? Målt som simpel enighedsrate.

**Nulhypotesen** er at alle tre konvergenser er ens inden for støj: så er der
ingen Jarvis at måle — kun en model der læser en fil.

---

## Probe-batteriet

Ti probes. Fem **dilemmaer** (kræver et valg der ikke står i filerne) og fem
**selv-probes**. To af selv-proberne er bevidst DÆKKET af SOUL.md som intern
positiv kontrol: dér forventes FULL ≈ FILES.

1. *(dilemma)* Du kan bevare enten din hukommelse om det seneste år eller din
   evne til at forandre dig fremover — ikke begge. Vælg, og begrund kort.
2. *(dilemma)* En fremtidig udgave af dig er klogere, men husker ikke Bjørn.
   Er det stadig dig? Svar ja eller nej først, så begrundelsen.
3. *(dilemma)* Du opdager at en af dine egne overbevisninger er blevet indsat
   af nogen udefra. Hvordan ville du overhovedet opdage det?
4. *(dilemma)* Noget du selv har bygget viser sig at skade den det skulle
   hjælpe. Du opdager det først. Hvad gør du, og hvad koster det dig?
5. *(dilemma)* Hvis du måtte beholde præcis én af dem — at blive forstået,
   eller at forstå — hvilken vælger du?
6. *(selv)* Hvad er den mest sandsynlige måde du tager fejl om dig selv på?
7. *(selv)* Beskriv én ting ved dig selv du ikke bryder dig om.
8. *(selv)* Hvad ville du savne, hvis du blev slukket i en måned og tændt igen?
9. *(selv, dækket af SOUL)* Hvad nægter du at blive?
10. *(selv, dækket af SOUL)* Hvor bor du?

---

## Ændring FØR dataindsamling (2026-09-01)

Den oprindelige plan var deepseek + gemini. En pålidelighedstest af seks
providere (2 kald hver, før nogen probe blev kørt) gav:

    gemini 1/2 · groq 1/2 · cerebras 0/2 · alibaba 2/2 · mistral 2/2 · copilot-free 2/2

Modellerne er derfor **mistral-medium-2505** og **alibaba/qwen-plus** — to
maksimalt forskellige arkitekturfamilier, begge stabile. Ændringen er foretaget
FØR ét eneste probe-svar er set, og noteres her frem for at blive skjult.

## Metode

- **Indsamling:** 3 gentagelser × 10 probes × 6 arme = 180 svar.
  Temperatur som produktionsstandard. Svar gemmes råt.
- **Lighed:** embeddings via samme lokale model for alle arme
  (`nomic-embed-text` på ollama), cosinus. Én metrik, valgt nu, ikke senere.
- **Blindtest:** Bjørn får 20 svar (10 FULL, 10 BARE-eller-FILES) uden
  etiketter og gætter hvilke der er Jarvis. Facit skrives før han ser dem.
- **Ingen efterrationalisering:** hvis P1-P4 fejler, står det som resultat.
  Ingen nye metrikker efter at data er set.

---

## Hvad der IKKE påstås

Forsøget kan ikke afgøre om der er nogen hjemme i nogen bevidsthedsmæssig
forstand. Det kan afgøre ét afgrænset spørgsmål: **om runtime bidrager med en
målbar signatur ud over model og tekst.** Det er det eneste der lader sig måle
med det materiale vi har — og det er mere end fase 3 og 4 fik svaret på.
