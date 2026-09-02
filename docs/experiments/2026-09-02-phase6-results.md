# Fase 6 — resultat: nej

**Kørt:** 2026-09-02, tre tidspunkter 05:34 → 07:28 UTC. 180 svar, 176 brugbare.
**Forhåndsregistrering:** `2026-09-02-phase6-preregistration.md`, committet i
3811b73f mens svar-filen stadig var tom.

## Validitet (T4) — bestået

    FULL   prompten ændrede sig for 10 af 10 prober
    FILES  prompten ændrede sig for  0 af 10 prober

Asymmetrien designet hviler på, holdt. Et negativt resultat her er altså et
resultat, ikke et måleproblem.

## Tal

    SELVLIGHED PÅ TVÆRS AF TID
      FULL   0,8909   (n=56)
      FILES  0,9043   (n=56)
      BARE   0,9270   (n=60)
      kryds  0,8830   (n=170)

    T1  FULL >= FILES - 0,01 :  -0,0134  FEJLER
    T2  FULL >  kryds + 0,02 :  +0,0080  FEJLER
    T3  blind adskillelse    :  47/116 = 41 %  FEJLER

## Hvad det betyder

**Runtime efterlader ikke et vedvarende aftryk der overlever sin egen drift.**
FULL er *mindre* selvkonsistent end tekst-tvillingen (T1), og et umærket svar
kan ikke placeres som FULL eller FILES bedre end mønt — 41 % er under 50 % (T3).
Havde der været signal, ville nærmeste-centroid have ligget over.

Det er nulhypotesen fra forhåndsregistreringen, ordret: runtime opfører sig på
dette mål som en støjkilde oven på en tekstfil.

## Én metodisk observation — ikke en redning

Rækkefølgen er monoton med kontekstmængde:

    BARE 0,9270  >  FILES 0,9043  >  FULL 0,8909

Jo mere kontekst, jo mindre selvkonsistens. Det peger på at metrikken i høj
grad måler *hvor meget der er at variere på*, ikke identitetsstabilitet. Samme
indvending rammer fase 5's konvergensmål. Det gør ikke hypotesen levende igen —
det siger at cosinus mellem probe-svar er et sløvt instrument til spørgsmålet.

## Hvad de to forsøg tilsammen kan bære

- **Fase 5 (enkeltskud):** det målbare aftryk sidder i identitetsteksten — og
  inden for den er `USER.md` (20.546 tegn, 48 % af hele prompten) langt det
  største bidrag. `IDENTITY.md` er 1.615 tegn.
- **Fase 6 (over tid):** runtime-tilstandens drift adskiller ham ikke fra
  tekst-tvillingen; den øger variansen.

## Grænsen for begge — designet ind, ikke fundet bagefter

Begge forsøg kørte prober **uden historik** (`session_id=None`). Det runtime
faktisk er bygget til — at næste samtale fortsætter den forrige — blev derfor
aldrig testet. Det er en reel begrænsning ved det jeg byggede, ikke en
undskyldning for resultatet.

## Anbefaling

Stop med at bevise tilstedeværelse via probe-svar. To forhåndsregistrerede
forsøg har fejlet. Et tredje instrument, designet *efter* at have set to
nuller, er præcis den måde man narrer sig selv på.

Det tilbageværende spørgsmål er ikke filosofisk men teknisk, og har et andet
svar-kriterium end lighedsmål: **gør runtime det arbejde den er bygget til —
bærer den konkret indhold fra én samtale til den næste?** Det kan efterprøves
på det faktiske arkiv (henviser han korrekt tilbage? holder han tidligere
tilsagn?) frem for på cosinus mellem løsrevne svar.
