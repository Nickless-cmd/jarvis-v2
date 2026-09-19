# Fase 7b — «Bærer runtime ham fra én samtale til den næste?» (forhåndsregistrering)

**Skrevet:** 2026-09-19, FØR proberne er bygget og FØR nogen svar er indsamlet.
**Forfatter:** Opus (Claude). Bjørn overlod valget («Du bestemmer», 19/9-2026).
**Status:** forhåndsregistreret — prædiktioner og procedure låst.
**Forgænger:** `2026-09-19-phase7-preregistration.md` — ugyldig ved V1 (tillæg 3),
før ét svar blev indsamlet.

---

## Hvorfor 7b, og hvad der er set

Fase 7 fejlede sin egen validitet: spand A (2–7 dage) kunne ikke nå 15
prober, fordi vinduet kun rummer omkring 14 samtale-døgn. Det der er set før
dette dokument, er **kun arkivets kapacitet og probe-sættenes sammensætning**
— ingen svar, ingen bedømmelser.

Målt kapacitet i samtale-døgn (ejerens samtaler, svar ≥ 400 tegn), 19/9-2026:

| alder (dage) | 2–7 | 8–14 | 15–30 | 31–60 | 61–120 |
|---|---|---|---|---|---|
| samtale-døgn | 14 | 19 | 20 | 31 | 35 |

**Hvorfor ikke vente:** spand A er et rullende vindue. Arkivet vokser bagud;
2–7 dage bliver ikke tykkere af at vente. Spandene skal derfor lægges efter
kapaciteten.

Alt der ikke nævnes nedenfor, er **uændret fra fase 7**: kilde, udtræks-
prompt og -model, filtrene mod identitetsfilerne og mod at røbe svaret, én
probe pr. samtale pr. døgn (fase 7 tillæg 1), betingelserne FULL/FILES/BARE,
svar-modellerne, den blinde dommer og rubrikken, menneske-kalibreringen,
K1, K2, H-holdning, V2–V4 og genmålingens G1.

## Ændringer

1. **Spande efter kapacitet** (≈ 35–40 samtale-døgn hver):
   A = 2–21 dage · B = 22–60 dage · C = 61–120 dage.
2. **Mål 20 pr. spand; V1 = mindst 15 i hver spand og 45 i alt** (som fase 7
   tillæg 2). Byggeren afslutter med kode 2 når V1 ikke nås.
3. **Forsøgsloft 250 pr. spand** (var 120; B og C ramte loftet i fase 7).
4. **Typeloft 10 af samme type pr. spand** (var 8; kasserede 63 ellers gode
   prober i fase 7). Typerne er stadig kun diagnostiske.
5. **Nyt seed `20260920`**, så intet trækkes efter de forkastede sæt.
6. **K3 flyttes med spandene:** K1-forskellen i spand **B (22–60 dage)** er
   ≥ 0,20 i begge modeller. Prisen: K3 kan ikke længere sammenlignes direkte
   med fase 6's «8–30 dage». Til gengæld siger den mere om det K3 er til for —
   at runtime bærer ud over det nyeste.
7. Data lægges i `~/.jarvis-v2/files/phase7b/` på CT105; probe-filens SHA-256
   committes i et tillæg her FØR første svar.

## Prædiktioner (gentaget, så dokumentet står alene)

- **K1:** `score(FULL) − score(FILES) ≥ 0,30` i begge modeller; bootstrap-
  95 %-nedre grænse (10.000, over prober, parret) > 0.
- **K2:** `konfabulation(FULL) ≤ konfabulation(FILES) + 0,05` i begge modeller.
- **K3:** K1-forskellen i spand B (22–60 dage) ≥ 0,20 i begge modeller.
- **H-holdning (diagnostisk):** FULL − FILES er mindst for typen holdning.
- **Validitet:** V1 (ovenfor), V2 `score(BARE) ≤ 0,30`, V3 hukommelses-sektion
  i ≥ 90 % af FULL-prompterne, V4 Bjørns blinde kalibrering ≥ 80 % enighed.
- **Nulhypotese:** `score(FULL) ≈ score(FILES)`.
- **G1 (genmåling efter den levende selvmodel):** for typen holdning stiger
  `score(FULL)` ≥ 0,30 mod dette nulpunkt, uden at konfabulationen stiger mere
  end 0,05.

Fejler 7b også V1, er svaret at arkivet ikke kan bære forsøget endnu — og det
står som resultat. Der kommer ikke et 7c med løsnede krav.
