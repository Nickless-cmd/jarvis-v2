# Play Console — App access (#7)

> Skrevet 28/9-2026. Dette er pakken til Plays «App access»-felt: hvordan en
> reviewer kommer ind i appen, og hvad det koster.

## Problemet

Appen er ubrugelig uden en Jarvis-server og et token. En reviewer der
installerer den fra Play, møder `LoginScreen` med to felter — **API** og
**Bearer token** — og en QR-knap. Uden credentials kan de ikke komme
videre, og så bliver appen afvist som «ikke funktionel».

Det er præcis hvad Play's *App access*-felt findes til: man giver
revieweren de oplysninger der skal til.

## Den konkrete vej

Appen peger allerede på Bjørns server som standard
(`DEFAULT_API_BASE_URL = 'https://api.srvlab.dk/'` i `apps/mobile/src/lib/types.ts`).
Så revieweren skal kun have **ét** token — URL'en står i feltet allerede.

```bash
python scripts/mint_jarvisx_token.py \
  --user-id play-reviewer \
  --role guest \
  --ttl-days 60 \
  --name "Google Play reviewer 2026-09"
```

Scriptet printer tokenet og skriver en post til
`~/.jarvis-v2/state/jarvisx_tokens.json` (audit-spor — tokenet gemmes
kun som preview, aldrig i fuld længde).

**Sådan udfyldes feltet i Play Console:**

```
Appen kraever login.

API:           https://api.srvlab.dk/
Bearer token:  <token fra scriptet>
```

## Hvorfor `guest`

`guest` er den mindst privilegerede rolle der findes
(`core/identity/household.py:33`), og den er **fail-closed**:

- Owner-værktøjer strippes (`core/tools/tool_scoping.py:44`)
- Ingen mutationer af control-planet (`core/tools/central_query_tool.py:26`)
- Ingen dispatch til kode-mode

Revieweren kan logge ind, se chatten, tale med Jarvis og gennemgå
indstillingerne. De kan ikke ændre systemet, ikke læse Bjørns historik
(guest har eget workspace), og ikke nå nogen af de værktøjer der rører
maskinen.

## ⚠️ Risikoen du skal kende

**Tokens kan ikke trækkes tilbage enkeltvis.** De er selvstændige JWT'er —
`verify_token()` slår intet op i en database, den verificerer kun signaturen
(`core/runtime/jarvisx_auth.py`). Den eneste udløbsmekanisme er:

1. **TTL** — tokenet udløber af sig selv (clampes til 1–365 dage)
2. **Roter `jarvisx_auth_secret`** i `runtime.json` — men det dræber
   **alle** tokens, inkl. Bjørns egne på desk, mobil og Mikkels maskine

Der findes ingen per-token revokeringsliste. Giver man et token til Google,
ligger det i deres system indtil det udløber.

**Anbefaling:** kort TTL (60 dage er nok til en gennemgang), og mint et nyt
hvis appen skal revurderes. Så dør adgangen af sig selv.

Den rene løsning — en revokeringsliste — er en kodeændring, ikke et dokument.
Den er lille (en liste i `verify_token`), men den rører auth-stien, så den
skal besluttes bevidst.

## Hvad der stadig mangler

1. **Beslutningen:** skal der mintes et token nu, eller venter vi til appen
   faktisk skal indsendes?
2. **Test af vejen:** er `api.srvlab.dk` faktisk nåelig udefra med et
   guest-token, og ser en guest en brugbar app? Ikke verificeret — der er
   ikke mintet et token endnu.
3. **Baggrundsplacering:** Play-bygget har den ikke (Vej B, 28/9), så
   reviewerens app vil ikke spørge om den tilladelse. Det er med vilje.
