"""Én linje i turens hale, lige dér hvor svaret bliver skrevet.

Bjørn 30/10-2026: «hvordan gør vi dig bedre til at huske suggest_next_task i
code mode før du afslutter med slut beskeden?»

MÅLT, ikke gættet:

* Reglen FINDES allerede. ``output_discipline`` siger ordret «call it BEFORE
  your closing text block — never after». Men den ligger i PRÆFIKSET: ca.
  30.000 tegn fra slutningen, og inde i sin egen sektion på tegn 2.574 af
  3.636. Det er ikke en instruks tæt på beslutningen — det er en fodnote i en
  manual der læses bagfra.
* ``suggest_standing_guard`` FINDES også og fyrer ved tur-afslutning. Den er
  koblet på ``visible_runs.py`` — samme løkke som code mode bruger — men den er
  slået FRA, fordi den kalder ``continue``: ``done`` skubbes, og slutsvaret skal
  flytte sig ud af et hoved der allerede er klappet sammen, midt i streaming.
  Det er Bjørns egen «teleportering» 19/10. At tænde den igen uden at løse det
  er at genindføre en fejl han allerede har betalt for.
* Kaldene faldt fra 382 i døgnet (19/10, vagten tændt) til 32–59 om dagen
  derefter. Prompt-linjen alene bærer ikke adfærden.

FORMLEN. ``RundeHale.tilfoej_vedvarende(art=RAADGIVNING)`` koster NUL runder:
halen er append-only, så cache-præfikset er urørt, og en RAADGIVNING er per
definition ikke grund til at fortsætte turen. Noten siger ikke «kald værktøjet
nu» — den siger hvad der gælder NAAR svaret skrives. Et nej er et gyldigt svar.

HVORFOR VEDVARENDE OG IKKE PER RUNDE. Den runde hvor svaret skrives kan ikke
kendes på forhånd: løkken ser først at turen slutter, når runden er returneret
uden værktøjskald. Og i den SIDSTE runde fjernes værktøjerne fysisk, så der kan
noten ikke ligge. En note der kun gælder én runde ville derfor aldrig være til
stede i den runde den handler om. Den lægges derfor ÉN gang pr. tur og bliver
stående — kaldet styrer selv at det kun sker én gang.
"""

from __future__ import annotations


def suggest_tail_note(*, already_sent: bool = False) -> str:
    """Noten til turens hale. "" når den allerede er lagt i denne tur.

    ``already_sent`` er kalderens flag, ikke en tilstand her: funktionen er ren,
    så den kan testes uden en kørende løkke, og så det er synligt i
    kaldestedet at noten kun må lægges én gang pr. tur.
    """
    if already_sent:
        return ""
    return (
        "📌 Når du skriver din afsluttende tekstblok: efterlader turen et næste "
        "skridt, så kald suggest_next_task FØR teksten — med skridtet i Bjørns "
        "ord, én linje, højst ti ord, en ordre han kunne sende. Det er sidste "
        "øjeblik: et kald efter svaret skubber folden og tvinger en ekstra "
        "runde. Er tråden reelt afsluttet, spring det over — et tomt felt er "
        "ærligt, et opdigtet skridt er ikke."
    )
