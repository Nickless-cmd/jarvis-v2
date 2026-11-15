# Holdbar open-loop-lukning

## Intent

Nye runtime-afledte open-loop-signaler skal fra fødslen have en registry-tråd,
så de kan lukkes med bevis. Samtidig skal inaktive tråde fortsat forfalde, og en
fast grænse skal forhindre ubegrænset ophobning og den afledte CPU-feedback.

## Constraints

- Den normale oprettelsesvej ejer tråd-oprettelsen; ingen efterfølgende backfill.
- De 118 eksisterende produktionsrækker ændres ikke.
- Bevis-lukning og inaktivitets-udløb er forskellige terminale veje.
- Et lukket signal må aldrig muteres tilbage til åbent.
- Det aktive loft er 128 og defineres ét sted.

## Approach

Den valgte løsning udvider open-loop-upsert med en valgfri tråddeklaration. Når
upsert faktisk indsætter en ny aktiv række, oprettes tråden i samme
DB-transaktion og bindes til signalet. Eksisterende rækker genbruges uden
retroaktiv tråd. Ved loftet rejser lageret en specifik fejl; servicelaget gør den
synlig i både resultat og eventbus.

Alternativet at oprette tråden før upsert blev fravalgt, fordi et efterfølgende
upsert-fejl ville efterlade en forældreløs tråd. En schema-migration/backfill blev
fravalgt, fordi beslutningen specifikt placerer ansvaret ved oprettelsen og
forbyder et efterfølgende patch-job.

Inaktivitets-refresh markerer også tråd-bundne loops stale. Efter det ekstra
vindue udløber registry-tråden eksplicit uden at skrive falsk closure-evidence,
og signalet lukkes med en sand udløbsårsag. Bevis-lukning forbliver den eneste
vej, der hævder at spørgsmålet er besvaret.

Lukkede rækker fjernes fra upserts merge-population. En senere observation med
samme canonical key bliver derfor en ny række/tråd, mens den gamle lukkede række
og dens begrundelse forbliver uændret.

