# Ollama-saldo-vagt — målingen modsagde præmissen

**Opgaven antog** at rutine-køen frøs 05:00-05:35 fordi ollama-kontoen var tom.
**Målingen siger noget andet.**

## Målt
- Ollamas journal: HTTP 200 på ALLE `POST /api/chat` 05:08-05:30; ingen ikke-200 i vinduet.
- `GET ollama.com/api/usage` giver kun forbrug (`usage_usd`, tokens) — INGEN saldo.
  `/api/me`, `/api/account`, `/api/billing` findes ikke. `/api/tags` er intet signal.
- Forkert nøgle → 401 `{"error":"Unauthorized"}`.
- Hvad et kald returnerer ved reelt tom saldo er **ikke målt** (kan ikke tømmes, ingen log har det).
  Derfor kan en «tom konto»-detektor ikke bygges før et kald; den ville være en gætning.

## Sandsynlig årsag til de 20 minutter (ikke bevist)
Kørslerne blev `session_dispatched`, dvs. sessions-routing. `route_next` returnerede
`pending` med en grund (`active-run`, `no-valid-session` …) og kastede den væk. En
visible-kørsel i ejerens session var aktiv 05:05-05:14. Ikke undersøgt til bunds hvorfor
ventetiden varede til 05:35.

## Bygget
1. `RoutineRunner.run_next` skriver et `waiting`-event med `reason` ved hver `pending`
   (ét pr. kørsel+grund, fast `event_id`). Det er DEFEKT 1 uanset årsag.
2. `core/services/ollama_balance.py`: ægte 1-token-probe, cachet 60 s. 200 → healthy;
   HTTP-fejl → blocked med status+tekst VERBATIM (ingen påstand om «tom saldo»);
   transportfejl → unknown (fail-open). Kun brugt mens en kørsel allerede venter og
   lanen er ollama.
3. Blokeret → `waiting`-event `ollama_blocked` + besked til ejeren (inbox + app-chat), én gang pr. kørsel pr. proces.

## Ikke gjort
- `dispatch_quota.py` er urørt: ingen målt ollama-kvote at lægge der.
- Selve ventetidens rodårsag (sessions-routing) ligger i `routine_dispatch.py`, uden for scope.
