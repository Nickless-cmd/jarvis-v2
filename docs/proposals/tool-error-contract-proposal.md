# Forslag: fælles årsagskode i værktøjsfejl

Status: forslag til gennemgang, 29/9-2026. Ingen værktøjskontrakt er ændret.

## Måling før design

Målt på CT105's levende DB i read-only-tilstand 29/9-2026: `events` har 83.006
`tool.completed`-events. 1.336 har `status: error`; 1.249 payloads har kun
`{status, tool}` og 87 har `{mutating, status, tool}`. De indeholder derfor
**ikke** værktøjets egentlige fejlobjekt. 295 `tool.error`-events har
`{error, source}`. En søgning efter `result_status == "error"` i
event-payloads gav 1.336
`runtime.executive_action_outcome_recorded`-events, som er et andet subsystem.
Det ville være en forkert måling at kalde disse 1.336 for værktøjsfejl; det
er et særskilt event-felt og subsystem, selv om antallet her er ens.

En AST-gennemgang af aktuel `core/tools/` finder 799 bogstavelige dict-udtryk med
`status: error` i 81 filer. 629 har `{status, error}`, 92 har `{status, text}`,
12 har `{status, reason}`, og resten har flere specialfelter. Det er antal
retursteder i kode, ikke antal fejl i drift. `central_error_envelope.py`
former brugerbeskeder og hændelser; `error_healers.py` former healer-resultater;
ingen af dem er i dag den ensartede returværdi fra hvert værktøj.

## Foreslået form

En fejl fra et værktøj returneres som et dict, så eksisterende kaldere stadig
kan læse `status`. De nye felter er faste:

```json
{
  "status": "error",
  "error": {
    "reason": "not_found",
    "message": "File not found: /path",
    "retryable": false,
    "details": {},
    "correlation_id": "run-id"
  }
}
```

`reason` vælges fra en lukket liste: `invalid_input`, `not_found`,
`permission_denied`, `approval_required`, `unavailable`, `timeout`,
`rate_limited`, `conflict`, `failed_precondition`, `execution_failed`,
`internal_error`. `message` er læsbar prosa og må ikke bruges til forgrening.
`details` må kun indeholde ufarlige, strukturerede data; rå exceptions og
credentials hører ikke hjemme der. `retryable` er et eksplicit råd til
kalderen, ikke en erstatning for approval- eller policy-gaten.

## Migration, hvis forslaget godkendes

1. Mål de faktiske returværdier i en kontrolleret prøve eller ved at logge
   kun feltnavne og årsagskoder. De eksisterende `tool.completed`-events kan
   ikke bruges til at rekonstruere fejltekst eller præcis form.
2. Indfør en fælles konstruktør og validator. Lad den eksisterende
   `status` blive, og udsend midlertidigt legacy `text`/`error`-strenge hvor
   kaldere kræver dem. Fejl i telemetri eller klassifikation må ikke vælte
   værktøjskaldet.
3. Migrér værktøjsfamilier én ad gangen, med tests af hele resultatobjektet
   og hver af de lukkede årsager. Mål ukendte årsager før et legacy-felt
   fjernes. En ny årsag kræver eksplicit kontraktændring.

Dette er en kontraktændring på tværs af værktøjerne. Den kræver en separat
beslutning før implementation.
