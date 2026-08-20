# infra/ — værktøjer der lever på værterne, ikke i Jarvis' runtime

Disse scripts kører på PVE-værterne og i llm-gateway-containeren. De ligger her
for at være versionerede og læsbare — **den kørende kopi er den på maskinen**.
Ændrer du noget her, skal det kopieres ud igen (sti står i hver fil).

Skrevet under migrationen 20. aug 2026, hvor pfSense + pihole + WebServices +
home-assistant flyttede fra Z390 til M900. Se `MIGRATION-M900-PLAN.md`.

## Nuværende topologi

| Vært | Adresse | Kører |
|---|---|---|
| **M900** (i5-6500T, 16 GB, vPro/AMT) | `10.0.0.2` | pfSense, pihole, WebServices, home-assistant |
| **Z390** (i9-9900K, 32 GB, GTX 1070) | `10.0.0.36` | Jarvis, llm-gateway, fileserver |

Bro-navnene betyder **forskellige ting** på de to maskiner, fordi kablerne
sidder i forskellige porte:

| | M900 | Z390 |
|---|---|---|
| `vmbr0` | WAN | LAN |
| `vmbr1` | LAN | DMZ |
| `vmbr2` | DMZ | (ubrugt) |

Flytter du en guest mellem værterne, **skal `bridge=` rettes** — ellers havner
den på det forkerte net. Home-assistant landede kortvarigt på WAN af netop den
grund.

## pve/

### `identify_ports.sh` → `/root/` på PVE-værter
Lytter passivt på hver port med link og fortæller hvilket subnet der er på
hvilken. Sender intet, ændrer intet. Brug den **før** broerne konfigureres —
så gætter man ikke på hvilket kabel der sidder hvor. Fandt 20. aug at WAN- og
DMZ-kablerne var byttet om.

### `net-selfheal.sh` → `/root/` + `net-selfheal.service`
Kører efter `networking.service`. Har `vmbr1` (management) intet link, leder
den de øvrige porte igennem efter LAN-trafik og flytter den rigtige port ind i
broen. Sikkerhedsnet mod at et kabel i den forkerte port låser dig ude.
Rører kun noget hvis `vmbr1` er nede; ruller tilbage hvis det ikke hjælper.

### `safe_shutdown.sh` → `/root/` på PVE-værter
Lukker alle guests i rækkefølge — **pihole og pfSense til sidst**, for der ryger
SSH-forbindelsen — verificerer hver enkelt er nede, og slukker så værten.
Køres detached (`setsid`), så den overlever at netværket forsvinder undervejs.
`poweroff`, ikke `reboot`: en ATX-PSU holder +5VSB så længe stikket sidder i,
så kun en fysisk afbrydelse nulstiller strømlaget.

### `expressvpn-boot-connect.sh` → `/usr/local/bin/` i llm-gateway (CT106)
Forbinder ExpressVPN ved boot. **Region skal være USA** — cheap-lanens account2
skal have både anden IP og anden geografi end account1, ellers kan providere se
dem som samme kilde.

Tre fejl rettet 20. aug (hver fundet ved en genstart-test):
1. `connect denmark` var hardkodet og overtrumfede alt andet
2. Løkken godkendte på `connectionstate=Connected` alene → en dansk tunnel
   talte som succes. Nu kræves også korrekt region.
3. Den kaldte `connect` hvert 5. sekund — også midt i et handshake — og
   afbrød sit eget forsøg. **100 s → 35 s** da det blev rettet.

`expressvpn-connect.service` har `Before=tinyproxy.service`, så cheap-lanens
proxy først åbner når tunnellen står. Melder servicen sig færdig for tidligt,
slipper trafik ud på egen IP — derfor logger scriptet nu både succes og fiasko
(`journalctl -t expressvpn-boot`).

## Fælder værd at huske

- **`pct set -netX` uden `hwaddr=` genererer en NY MAC.** Alle DHCP- og
  DHCPv6-reservationer holder så op med at matche. Angiv altid `hwaddr`.
  Original config findes i backuppen:
  `tar -I zstd -xOf <backup> ./etc/vzdump/pct.conf`
- **Global IPv6 kommer fra DHCPv6-reservationer** (`2001:470:6c:b5::100:N/128`),
  ikke SLAAC. `ip6=auto` alene giver kun ULA (`fd93:…`). Efter genstart kan en
  container mangle sin globale adresse — fix: `dhclient -6 <iface>` indeni.
- **pfSense afviser DHCP-reservationer inde i poolen** (DMZ: `.25–.254`), men
  fejlbeskeden lyver og påstår overlap med en static mapping der ikke findes.
- **pfSense REST API:** header `X-API-Key` (ikke `Authorization`), base
  `https://10.0.0.1/api/v2`. Nøgle i `~/.jarvis-v2/config/runtime.json`.
