# Selvhostet ntfy — alarmer ud af den offentlige tredjepart

Sat op 8/10-2026. Erstatter `ntfy.sh` som kanal for push til Bjørns telefon.

## Hvorfor

Målt 7/10-2026: alarmer gik til `ntfy.sh/<topic>` **uden adgangskontrol**.
Et uautentificeret `curl` svarede 200 med hele historikken — 32 beskeder på
12 timer, blandt dem helbredsoplysninger (medicin-påmindelser), værtens
temperaturer og driftsomkostninger.

To ting blev rettet dengang, og én manglede:

1. ✅ Emnenavnet stod i den offentlige kilde (repoet svarer 200 uden auth) —
   fjernet i `9a02bfcd6`, og en vagt (`tests/test_ntfy_topic_ikke_i_kilden.py`)
   holder det væk.
2. ✅ Intern støj: `ambient_presence` sendte hver faseovergang til telefonen
   (14 af 31 beskeder). Flyttet til Centralens eget spor.
3. ❌ **Serveren var den samme.** Et uopdageligt navn skjuler kanalen men
   beskytter den ikke — enhver der får navnet kan læse alt. Og `ntfy.sh`s
   adgangskontrol kræver en betalt plan (Supporter $5-6/md, Pro $12/md).

Punkt 3 er denne opsætning.

## Hvad der kører

| | |
|---|---|
| Container | **CT 107** `ntfy` på i9 (`10.0.0.36`) — uprivilegeret, 2 cores, 1 GB, 4 GB disk |
| IP | `10.0.0.107/24`, gw `10.0.0.1`, `onboot: 1` |
| Software | Debians egen pakke `ntfy` 2.11.0 (`apt install ntfy`) — ingen tredjeparts-binary |
| Port | `2586` (HTTP) |
| Config | `/etc/ntfy/server.yml` |
| Auth-DB | `/var/lib/ntfy/user.db` |
| Cache | `/var/cache/ntfy/cache.db` (48 t) |
| Service | `ntfy.service`, kører som brugeren `_ntfy` |

**Hvorfor ikke i Jarvis-containeren (CT 105):** en alarmkanal må ikke dø med
det den alarmerer om. Ligger ntfy inde i CT 105, kan den ikke melde at CT 105
er nede. Samme grund til at den ikke ligger i webserveren.

### Adgangskontrol

`auth-default-access: deny-all` — intet kan læses eller skrives uden en
gyldig bruger eller et token. Tre brugere, mindste privilegium:

| Bruger | Rolle | Adgang | Bruges af |
|---|---|---|---|
| `bjorn` | admin | alt | administration, verifikation |
| `jarvis` | user | rw på emnet | gateway'en (token) |
| `phone` | user | rw på emnet | ntfy-appen på telefonen |

Adskilte brugere betyder at en tilbagekaldelse af det ene token ikke rører
det andet.

## Telefonen

Bjørns telefon er en **Samsung Galaxy S24 (Android)**. På Android bruger
selvhostet ntfy **instant delivery** — appen holder selv en WebSocket åben.
Firebase/FCM bruges **kun** af `ntfy.sh` og af Play-versionen mod den vært;
mod en selvhostet server er der ingen tredjepart i kæden.

På iOS er det anderledes: Apple tillader ikke baggrundsforbindelser, så en
selvhostet server skal videresende til `ntfy.sh` via `upstream-base-url`.
Det er ikke relevant her, men det er derfor valget af telefon betyder noget.

## Vejen ud — Cloudflare-tunnelen

WAN er bag CGNAT, så indgående port-forwarding er umulig. Eneste vej til
telefonen på 4G er den eksisterende cloudflared-tunnel på webserveren
(VM 101, `10.0.0.12`).

**Sat op 8/10-2026.** Ingress tilføjet i `/etc/cloudflared/config.yml` som
regel #7, **før** catch-all-linjen `http_status:404`:

```yaml
  - hostname: ntfy.srvlab.dk
    service: http://10.0.0.107:2586
```

Plus DNS: CNAME `ntfy` → `9184924a-c751-4441-b4d5-daf34ed26869.cfargotunnel.com`,
oprettet med `cloudflared tunnel route dns`.

### Adgangsvejen (målt 8/10-2026)

To ting holdt mig først tilbage, og begge var forkerte:

- `sudo` på `10.0.0.12` kræver password — men **`ssh root@10.0.0.12` virker
  passwordless** (samme nøgle som `bs_jarvis`). Det var vejen ind hele tiden.
- `cert.pem` manglede «på nogen vært» — det var en måling taget som
  `bs_jarvis`, som ikke kan læse `/home/bs/`. Filen ligger på
  **`/home/bs/.cloudflared/cert.pem`** og er læsbar som root. Med den kan
  `cloudflared tunnel route dns` oprette recordet uden Cloudflare-login.

Læren: «jeg har ikke adgang» er en måling, ikke et faktum — den gælder den
bruger jeg målte som. Prøv root, før du melder en blokering.

`base-url: https://ntfy.srvlab.dk` og `behind-proxy: true` er sat i
`server.yml` fordi TLS termineres i Cloudflare.

### Verificeret udefra (8/10-2026)

| Test | Resultat |
|---|---|
| `https://ntfy.srvlab.dk/v1/health` | **200** |
| Emnet uden nøgle | **403** |
| Emnet med `phone`-token | **200** + beskederne |

Auth håndhæves altså gennem tunnelen — ikke kun på LAN.

`base-url: https://ntfy.srvlab.dk` og `behind-proxy: true` er sat i
`server.yml` fordi TLS termineres i Cloudflare.

## Skiftet (rækkefølgen er ikke valgfri)

En alarmkanal der ikke virker er værre end en offentlig en der gør. Derfor:

1. Tunnel + DNS på plads.
2. Verificér udefra: `curl https://ntfy.srvlab.dk/v1/health` → 200, og at
   emnet stadig svarer 403 uden nøgle.
3. Bjørn peger ntfy-appen på `https://ntfy.srvlab.dk` og logger ind som
   `phone`.
4. Send én test → **Bjørn bekræfter at den nåede telefonen.**
5. Først derefter skiftes `runtime.json`:
   ```json
   "ntfy_server": "https://ntfy.srvlab.dk",
   "ntfy_topic":  "<emnet>",
   "ntfy_token":  "<jarvis-token>"
   ```
   `ntfy_gateway._load_config` læser filen ved **hvert** kald — ingen cache,
   så skiftet virker uden genstart.
6. Send én alarm ad den nye vej og bekræft den på telefonen.
7. Ryd den gamle offentlige topic.

## Rollback

`ntfy_token` er **valgfrit**. Er feltet tomt, sender gateway'en præcis som
før mod `ntfy_server`. Rollback = sæt `ntfy_server` tilbage til
`https://ntfy.sh` og `ntfy_token` til `""`.

Containeren kan fjernes helt med `pct stop 107 && pct destroy 107` — den
deler intet med de øvrige containere.

## Hvad der IKKE er gjort

- Skiftet i `runtime.json` — bevidst, indtil telefonen er bekræftet.
- Den gamle offentlige topic er stadig aktiv.

## Filer

- `core/services/ntfy_gateway.py` — `_load_config` læser `ntfy_token`,
  `send_notification` sender `Authorization: Bearer`.
- `core/services/ambient_presence.py` — går kun på event-bussen.
- `tests/test_ntfy_topic_ikke_i_kilden.py` — vagt mod at navnet lækker.
