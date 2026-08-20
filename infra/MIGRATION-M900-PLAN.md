# Migration: pfSense + pihole → M900

**Læs denne lokalt — nettet er nede undervejs.**
Skrevet 20. aug 2026.

> ⚠️ **M900 OVERTAGER Z390's ADRESSER.** Efter genstart svarer M900 på
> **`10.0.0.2`** (ikke .29), plus `192.168.50.2` og WAN-broens
> `100.75.136.0/24` — adresse-for-adresse identisk med den gamle vært.
> **Z390 SKAL have nye adresser før den kommer på nettet igen som `pve-02`,
> ellers IP-konflikt.** pfSense driver selve nettet (10.0.0.1 / 192.168.50.1);
> værtsadresserne er kun til at nå PVE selv.

---

> 🛑 **GENSTART IKKE M900 FØR Z390 ER AF NETTET.** M900 tager nu `10.0.0.2`
> ved boot — den samme adresse Z390 har lige nu. Genstart før Z390 er nede
> giver øjeblikkelig IP-konflikt.

## Maskinen rejser sig selv — jeg behøver ikke være med

Alt er sat op så M900 kommer op **fuldt funktionel uden indgriben**. Det er
med vilje: i det øjeblik kablerne flyttes, er der ingen router på nettet, og
så kan ingen komme ind og rette noget bagefter.

- `link_down` **fjernet** fra pfSense WAN
- `onboot=1` på begge
- **Startup-rækkefølge:** pfSense `order=1`, pihole `order=2,up=15`
  (uden det ville pihole starte først, fordi VMID 100 < 103 — DNS før router)

## Status: alt er forberedt og testet

- pihole + pfSense **restaureret** på M900 (checksums verificeret identiske)
- Begge **test-startet og bevist at boote**: pihole-FTL aktiv; pfSense bragte WAN,
  LAN, HOMELAB, OPT3, WANV6, CARP, firewall, PFLOG og DNS Resolver op
- Begge er **stoppet igen** og venter
- MAC-adresser uændrede (vigtigt for din CGNAT-IP)
- Broerne `vmbr1` + `vmbr2` er oprettet, men **isolerede** (ingen fysiske porte endnu)

---

## Kabelplan

| Port på M900 | Bro | Net | Hvorfor netop den |
|---|---|---|---|
| **`eno1`** — indbygget Intel I219-LM | `vmbr1` | **LAN** 10.0.0.x | **AMT lever kun på denne port.** Skal være på LAN, ellers mister du remote-recovery og eksponerer AMT mod internet |
| **USB `7c:c2:c6:53:6b:6f`** (ASIX-driver) | `vmbr0` | **WAN** 100.75.x | Har den rigtige `ax88179_178a`-driver |
| **USB `c8:a3:62:e2:46:fb`** (cdc_ncm) | `vmbr2` | **DMZ** 192.168.50.x | Generisk driver — mindst trafik her |

**Rammer kablet den forkerte USB-port? Det er håndteret.** Kør bagefter:

```
/root/identify_ports.sh
```

Den lytter passivt på hver port og fortæller hvilket subnet der er på hvilken —
sender intet, ændrer intet. Derefter sættes broerne op efter hvad der FAKTISK
sidder hvor. Rækkefølgen af kablerne er altså ligegyldig.

---

## Rækkefølge på dagen

1. **Z390 helt af nettet FØRST** — ellers to DHCP-servere og IP-konflikt.
   `pct stop 100 && qm stop 103` på 10.0.0.2, eller træk dens kabler.
2. **Flyt kablerne** til M900 efter tabellen ovenfor.
3. **Genstart M900.** Nu træder alt i kraft: broerne bindes til de fysiske
   porte, værten tager 10.0.0.2, pfSense starter (order=1), pihole 15 s efter.
4. **Virker nettet?**
   - Ja → færdig. Sig til, så verificerer jeg broer, link-hastighed og driver.
   - Nej, men M900 svarer på `10.0.0.2` → kør `/root/identify_ports.sh`,
     byt `bridge-ports` om i `/etc/network/interfaces`, `ifreload -a`.
   - Nej, og ingen adgang → `net-selfheal.service` har forsøgt at finde
     LAN-porten selv (log: `/var/log/net-selfheal.log`). Ellers AMT eller
     skærm+tastatur.
5. **Test hastighed.** Holder det → flyt resten.
   Z390 får nye adresser og bliver `pve-02`, HP bliver `pve-03`.

---

## Hvis det går galt — rollback

Alt på Z390 er **urørt**. VM'erne dér er originalerne, kun stoppet.

1. Flyt kablerne tilbage til Z390
2. `pct start 100 && qm start 103` på 10.0.0.2
3. Du er tilbage hvor du var

**AMT er dit sikkerhedsnet på M900**: remote KVM og power selv når OS er dødt.
Aktiveres med Ctrl+P under boot (MEBx). Værd at sætte op *inden* migrationen.

---

## Fundet undervejs — allerede rettet

- **Thin pool uden beskyttelse på BEGGE værter.** Z390 var overprovisioneret
  (130 GB volumes på 123 GB pool, 44 % fuld) med `autoextend_threshold = 100`
  = ingen advarsel, ingen udvidelse. Løber en thin pool fuld, korrumperes
  *alle* volumes i den. Nu 80 %-tærskel begge steder, `dmeventd` overvåger.
- `pve-test`-repo var aktiv på M900 (testing-pakker i produktion) → deaktiveret
- `swappiness` 60 → 10 på M900 (hypervisor må ikke swappe VM-RAM)
- SSH-nøgle Z390 → M900 (kræves til clusteret senere)

## Ikke løst endnu

- **NVMe'en er fysisk fraværende** i M900 — ingen NVMe-controller på PCI overhovedet.
  Ikke et problem for planen (894 GB SSD rækker), men den 512 GB du troede sad der,
  er ikke i maskinen.
- Den ene USB-adapter binder til generisk `cdc_ncm` i stedet for `ax88179_178a`.
  Kan koste ydelse. Rettes når der er link at måle på.
- **RAM-loft:** M900 har 16 GB. Infrastrukturen (pfSense 2 + pihole 0,25 +
  home-assistant 4) fylder ~6,5 GB — masser af luft. Men Jarvis alene er
  allokeret 16 GB og skal blive på Z390 hos GPU'en.
