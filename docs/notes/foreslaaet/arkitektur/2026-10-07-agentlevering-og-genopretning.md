# Agentlevering og genopretning må ikke være best effort

Status: foreslaaet

## Problem

Jarvis kan allerede oprette agenter, gemme transcripts og modtage sene svar gennem en completion-/wakeup-vej. En agent kan dog arbejde færdig, mens Jarvis' synlige run stadig kører, en bro kan forsvinde efter et skrivende kald, og en proces kan dø mellem færdigt resultat og forælderens næste modeltrin. En chatnotifikation, en `get_agent`-henvisning eller en eventbus-hændelse alene kan ikke bevise, at Jarvis fik og behandlede udfaldet. Det nuværende transcript afkorter desuden læsevenlige toolresultater, så det kan ikke alene være den fulde redningskopi.

## Beslutning

Den foreslåede spec i `docs/specs/2026-10-07-agentorkestrering-og-subagenter.md` gør terminalt agentudfald og parent-inboxbesked til én varig DB-transaktion. Inboxen har særskilt accept-, leverings-, modelclaim- og acknowledgementstatus. Et aktivt Jarvis-run indlæser beskeden ved næste modeltrin; et inaktivt run vækkes i den oprindelige session. Samme besked-id må ikke give flere modelinputs. Supervisoren skriver også en terminal fejlbesked, hvis barnet ikke kan afslutte selv.

Hvert forsøg beholder komplette artefakter under Jarvis' runtime-home. `*.tmp`-filer afsluttes med flush, fsync og atomisk omdøbning; en DB-reference gør output hentbart, selv når kortversionen i prompten eller UI'et er afkortet. Brokald får stabil invocation-identitet. Et uvist udfald af et muligvis udført skrivende kald mærkes `outcome_unknown` og gentages ikke blindt. Langtidsagenter er varige identiteter med separate, lease-styrede runs.

## Overvejede alternativer

- **Kun eventbus eller pushnotifikation:** hurtig live-visning, men ingen sikker levering efter genstart og intet bevis for modelclaim.
- **Kun `get_agent`-polling:** resultatet kan hentes, men Jarvis kan glemme barnet eller afslutte uden at læse en fejl.
- **Kun transcript-JSONL:** nyttigt auditspor, men DB-transaktion med parent-inbox mangler, og nuværende toolresultater er afkortede.
- **Automatisk retry af alle brokald:** kan gentage skrivning, kommandoer eller eksterne handlinger, hvis forbindelsen brød efter udførelse.
- **Én lang, permanent proces pr. agent:** gør genstart, ejerskab og budgetkontrol skrøbelige; en stabil agentidentitet med afgrænsede runs kan genoptages mere kontrolleret.

## Konsekvenser

Der kræves en inbox/outbox, lease-ejerskab, idempotensnøgler, artefakt-retention og recovery-tests på tværs af runtime og klientbro. Desk i arbejdsmodus viser den projicerede sandhed og giver styringshandlinger; det er ikke en ny statusdatabase. Garantien er varig registrering og gentaget leveringsforsøg, indtil Jarvis' modeltrin har claimet beskeden. Den er ikke et løfte om, at et fjernskrivekald kan afgøres automatisk efter forbindelsestab, eller at et menneske har læst resultatet. `outcome_unknown` og behovet for verificering skal være synlige.
