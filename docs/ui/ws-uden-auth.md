# Event-socketen streamede hans indre liv til enhver der forbandt

**15/9-2026.** Fundet mens jeg byggede login til web-UI'en.

## Hvad der var galt

`/ws` kaldte `await ws.accept()` uden noget tjek. Middlewaren er registreret
som `app.middleware("http")`, så **WebSockets går uden om den helt**. Målt: en
forbindelse uden token gav straks rigtige interne events, og Caddy videresender
alle stier på det offentligt nåelige api.srvlab.dk (185.107.14.241).

Hvad der lå i strømmen — sidste time på bussen, målt før rettelsen:

```
runtime.cheap_lane_provider_completed   1.676
reasoning.conclusion.captured           1.144
thought_stream.fragment_generated         ← hans indre stemme
private_brain.continuity_completed
cognitive_state.somatic_body_updated
```

Det er ikke telemetri.

## Hvem der bruger den

| klient | steder | sendte token? |
|---|---|---|
| web-UI | `adapters.js:100` | nej |
| desk | `useCoworkData.ts`, `useMissionControl.ts`, `EventStream.tsx` | nej |
| mobil | — | bruger den ikke |

Mobilen har sin egen bro-socket, og **den var allerede beskyttet**:
`/api/jarvisx-bridge/ws` verificerer et Bearer-token i handshaket. Den der
bærer `operator_bash` var altså aldrig åben.

## Hvorfor subprotokol og ikke `?token=`

Browsere kan ikke sætte headers på en WebSocket. Den nærliggende udvej er en
query-parameter — og den er forkert her: uvicorns adgangslog skriver hele stien
med query, så hver eneste forbindelse ville lægge et **gyldigt token i
journalen**. `Sec-WebSocket-Protocol` kan browseren sætte, og den logges ikke.

Klienten byder `[jarvis-bearer, <token>]`; serveren bekræfter kun navnet.
Headeren accepteres også, for klienter der ikke er en browser.

Navnet står tre steder — `core/runtime/ws_auth.py`, web-UI'ens `auth.js`,
desks `api.ts` — og en test binder dem sammen. Driver de fra hinanden, fejler
forbindelsen tavst.

## Desk: tre kaldesteder, én hjælper

`openEventSocket(config)` i `lib/api.ts`. Tre kopier ville drive fra hinanden,
og den ene der blev glemt ville fejle **tavst**: socketen falder tilbage til
polling, så intet ser i stykker ud. En test afviser nu enhver rå
`new WebSocket(` i desks kildetræ uden for `api.ts`.

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| vagten fjernes fra ruten | 1 rød |
| `verificer` slipper fejl igennem | 2 røde |
| tomt token accepteres | 2 røde |
| protokol uden token tæller som legitimation | 2 røde |
| serveren bekræfter en protokol klienten ikke bad om | 8 røde |
| protokolnavnet driver fra hinanden | 3 røde |
| ruten afviser ALLE | 4 røde |
| dev-udvejen fjernes (låser localhost ude) | 2 røde |
| **desk-hjælperen dropper tokenet** | **overlevede først** |
| **`accept()` vælger altid en protokol** | **overlevede først** |

De to sidste er de vigtige.

Den første overlevede en kildevagt, fordi vagten undtog `api.ts` hvor hjælperen
selv bor. Desk har vitest, så den måles nu med en **rigtig** test der fanger
argumenterne til `new WebSocket` — og den fanger også «tokenet lagt i URLen».

Den anden overlevede fordi min integrationstest tillod både `None` og navnet.
Bekræfter serveren en protokol klienten ikke bad om, afviser browseren
forbindelsen — og det ville ligne et netværksproblem, ikke en fejl i koden.
Argumentet til `accept()` måles nu direkte.

## Både afvisning og accept er prøvet

En vagt der afviser alle er lige så ubrugelig som en der afviser ingen, og de
ni enhedstests kunne ikke se forskel. Der er nu en ægte ASGI-klient mod ruten
for begge sider, plus dev-udvejen (enkeltbruger-localhost uden auth).

## Hvad der sker for desk indtil en ny udgivelse

Desks nuværende binære sender intet token og bliver afvist. `ws.onerror`
falder tilbage til polling, så desk virker — bare uden live-push. Rettelsen
ligger i kilden og følger med næste release.
