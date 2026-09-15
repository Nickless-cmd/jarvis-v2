# Web-UI'en kunne ikke åbnes — login-siden lå bag login'et

**15/9-2026.** Bjørn: «apps/ui har ikk rigtigt nogen login side lige som desk
app og mobil app… og jeg kan ikk åbene den i min browser».

## Tre fejl oven på hinanden

**1. Døren var låst udefra.** `GET /` svarede `401 authentication required`.
Browseren kunne ikke hente den HTML der skulle logge ham ind.

**2. Der var intet login.** Ingen Google-knap, intet token-felt, og ingen
`Authorization`-header på nogen af UI'ens fem hentesteder. Men bagenden havde
vejen hele tiden — disse er **allerede public**: `/api/auth/login`,
`/api/auth/google/start`, `/api/auth/google/result`, `/api/auth/renew`.
Mekanismen fandtes; siden manglede.

**3. Fejlen var fanget og skjult.** `initialize()` fanger og gemmer fejlen i
`error` — men `App.jsx:33` returnerede boot-skærmen først:

```jsx
if (!shell) return <div className="boot-screen">Loading unified shell…</div>
```

`refreshShell()` kastede, så `shell` forblev `null`, så beskeden der
forklarede hvorfor blev aldrig tegnet. Derfor «Loading…» i evighed i stedet
for «du er ikke logget ind». Diagnosen fandtes; ingen viste den.

Dertil: `dist` på serveren var bygget **6. juli**, mens kilden er ændret 6.
september. `dist/` er gitignoreret, så den bygges på værten — og ingen havde
gjort det i to måneder.

## Hvorfor kun lokalt

`api.srvlab.dk` peger offentligt på 185.107.14.241 — den er nåelig udefra, og
det er sådan mobilen virker ude. En blank undtagelse ville derfor lægge
login-siden på internettet.

Bjørn: «Lad os bar holde den lokalt åben. Indtil jeg ved hvad jeg vil… de
andre bruger har pt. Discord, desk og mobil adgang og det er fint for nu».

Porten åbner **kun skallen** — `/`, `/index.html`, `/assets/*`, favicon. Hvert
`/mc/*` og `/chat/*` kræver stadig token. Uden login viser siden en
login-skærm og intet andet.

## Afsender-IP'en blev målt før den blev båret

Hele egenskaben hviler på at `request.client.host` ikke kan forfalskes. Det
blev målt, ikke antaget: tre kald gennem Caddy til api.srvlab.dk — ét rent, og
to med forfalsket `X-Forwarded-For` (`10.0.0.99` og `8.8.8.8`).

    10.0.0.20 - "GET /health?probe=ren"
    10.0.0.20 - "GET /health?probe=forfalsket"
    10.0.0.20 - "GET /health?probe=offentlig"

Alle tre blev logget som den ægte afsender. Caddy og uvicorn tager det
betroede hop, ikke klientens påstand.

Fejlretning: kan adressen ikke læses, er svaret **nej**. En dør man ikke kan
se hvem der står foran, skal blive lukket.

## Mutations-prøve

| Mutation | Udfald |
|---|---|
| offentlige adresser regnes også som lokale | 3 røde |
| ulæselig adresse åbner døren | 2 røde |
| tom afsender åbner døren | 3 røde |
| `/assets` uden skråstreg (præfiks-smuthul) | 3 røde |
| porten kobles fra i middlewaren | 1 rød |
| `_er_ui_skal` droppes (lokal = alt) | 2 røde |
| `_er_lokal_afsender` droppes (skallen åben for alle) | 2 røde |
| **OG → ELLER i middlewaren** | **overlevede først** |

Den sidste er den vigtige. `and` → `or` gør enhver lokal afsender til fuld
adgang uden token — og de to enhedstests kunne ikke se det, fordi de måler
hver betingelse for sig. **Beslutningen er sammensat, så den skal måles
sammensat.** Der er nu tre tests der kører den ægte middleware og bekræfter at
en lokal afsender får skallen, men ikke data.

## Verificeret i browseren

Login-skærmen tegnes. Et forkert token blev afvist med 401, tokenet ryddet fra
`localStorage`, og skærmen kom tilbage til login i stedet for at hænge — målt
i netværkspanelet, ikke gættet ud fra at skærmen så ens ud.

`apps/ui` har ingen testkørsel, så der er ingen enhedstests på login-skærmen.
Det er verificeret på enheden i stedet, og det siges her frem for at lade som
om der er dækning.

## Fundet undervejs — `/ws` er uden auth

Middlewaren er registreret som `app.middleware("http")`, så **WebSockets går
uden om den helt**. `/ws` kalder `await ws.accept()` uden noget tjek, og en
forbindelse uden token gav straks rigtige interne events
(`learning_pipeline.cycle_completed`). Caddy videresender alle stier på det
offentligt nåelige api.srvlab.dk.

Ikke rørt — desk og mobil kan bruge den, og en rettelse kan brække dem.
Afventer beslutning.
