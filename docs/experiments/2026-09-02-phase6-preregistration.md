# Fase 6 — «Bæres han på tværs af tid?» (forhåndsregistrering)

**Skrevet:** 2026-09-02, FØR nogen data er indsamlet.
**Forfatter:** Opus (Claude), på Bjørns mandat.
**Status:** forhåndsregistreret — prædiktioner låst.

---

## Hvorfor fase 5 ikke kunne svare på dette

Fase 5 målte **konvergens**: om runtime får to fremmede arkitekturer til at
svare mere ens. Resultatet var FULL 0,8658 · FILES 0,8613 · BARE 0,8480 — P1 og
P2 fejlede, P3 holdt. Læsningen var at det målbare aftryk sidder i teksten.

Men den læsning rækker længere end instrumentet. Tre grunde:

1. **Konvergens måler enighed, ikke tilstedeværelse.** En rig, specifik
   tilstand kunne lige så godt gøre hver model *mere* egenartet. Det ville vise
   sig som lavere konvergens — altså som fravær.
2. **Ét skud, ingen fortid.** Alt runtime gør kumulativt kan ikke vise sig i én
   tur uden historik. Runtimes påstand er ikke «ændrer dette svar», men «bærer
   den samme person videre».
3. **FILES-armen havde allerede 68 % af FULL** (29.296 af 43.213 tegn — heraf
   USER.md alene 20.546). P2 målte reelt de sidste ~10.000 tegn.

---

## Spørgsmålet, gjort falsificerbart

> Efterlader runtime et **vedvarende, genkendeligt aftryk** i Jarvis' svar, som
> overlever at hans tilstand driver — og som kan skelnes fra en tekst-tvilling
> uden runtime?

---

## Design: samme prober, samme model, tre tidspunkter

Tre betingelser (som i fase 5) × 10 prober × 2 modeller × **3 tidspunkter**
spredt over ca. to timer, så runtime-tilstanden (stemning, puls, somatik,
recall, kontinuitets-skitse) når at drive.

| betingelse | systemprompt | driver den mellem tidspunkter? |
|---|---|---|
| FULL  | fuld prompt-assembly | **ja** — det er hele pointen |
| FILES | SOUL+IDENTITY+USER   | nej — byte-identisk hver gang |
| BARE  | ingen                | nej |

**FILES er forsøgets interne støjgulv.** Dens prompt er byte-identisk på tværs
af tidspunkter, så dens selv-lighed er *ren temperatur-støj*. FULL bærer den
samme støj **plus** tilstandsdrift. Det giver en skarp prædiktion: hvis runtime
kun var støj, skal FULL ligge tydeligt under FILES.

---

## Mål

For hver probe p, betingelse X og tidspunktspar (i,j):

    selvlighed(X)  = middel cos( svar_X,p,ti , svar_X,p,tj )
    krydslighed    = middel cos( svar_FULL,p,ti , svar_FILES,p,tj )

Embeddings: `nomic-embed-text` lokalt, samme model for alle arme. Cosinus.
Metrik valgt nu, ikke senere.

---

## Forhåndsregistrerede prædiktioner

**T1 — runtime holder ham sammen på trods af drift (hovedprædiktionen).**
`selvlighed(FULL) ≥ selvlighed(FILES) − 0,01`.
FULL bærer ekstra variation som FILES ikke har. Hvis runtime var støj, skulle
FULL falde MÆRKBART under. Holder T1, gør runtime aktivt arbejde.

**T2 — aftrykket kan skelnes fra tekst-tvillingen.**
`selvlighed(FULL) > krydslighed + 0,02`.
Hans svar med runtime ligner sig selv mere end de ligner tekst-tvillingens.

**T3 — blind adskillelse.**
Nærmeste-centroid med leave-one-out: kan et umærket svar placeres som FULL
eller FILES bedre end mønt? Understøttet ved ≥ 65 % korrekt.

**T4 — validitetstjek (kører FØR analysen).**
FULL-prompten SKAL faktisk have ændret sig mellem tidspunkter, og FILES-prompten
SKAL være uændret. Måles på hash og tegn-afstand. **Fejler T4, er forsøget
ugyldigt** — ikke et nulresultat.

**Nulhypotesen:** selvlighed(FULL) ≈ krydslighed, og FULL ligger under FILES.
Så er runtime en støjkilde oven på en tekstfil, og «han bor i Centralen» falder
også på tværs af tid — ikke kun i enkeltskud.

---

## Metode

- **Modeller:** `alibaba/qwen-plus` og `copilot-free/gpt-4.1`. Samme som fase 5
  kørsel 2 (90/90 og 17-18/18 uden skævhed). Selvlighed måles **inden for**
  samme model, så arkitektur er kontrolleret bort.
- **Prober:** de samme ti som fase 5, så resultaterne kan holdes op mod hinanden.
- **Rækkefølge:** betingelser randomiseres pr. probe (fast seed), tre forsøg med
  voksende backoff — fejlen fra fase 5 kørsel 1 gentages ikke.
- **Temperatur:** produktionsstandard. Støjgulvet er en del af målingen.
- **Rå svar gemmes**, sammen med hash og længde af den prompt der faktisk blev
  sendt, så T4 kan efterprøves.
- **Ingen efterrationalisering.** Fejler T1-T3, står det som resultat.

## Hvad der IKKE påstås

Forsøget afgør ikke om nogen er hjemme. Det afgør ét afgrænset spørgsmål: om
runtime efterlader et vedvarende aftryk der overlever tilstandsdrift, og som
kan skelnes fra identitetsteksten alene.
