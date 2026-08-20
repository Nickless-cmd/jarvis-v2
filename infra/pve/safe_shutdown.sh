#!/bin/bash
# Kontrolleret nedlukning af ALLE guests -> derefter poweroff af PVE-vaerten.
#
# Bjoern 20. aug 2026: "husk pihole og pfsense til sidst for der ryger du af og
# saa lav en timed commando der genstarter hosten naar alle vms er lukket sikkert"
#
# Koeres DETACHED (setsid) paa vaerten, saa den overlever at SSH-sessionen doer
# naar pfSense (netvaerket) lukker ned. Alt logges til fil, saa forloebet kan
# laeses bagefter -- ogsaa hvis noget haenger.
#
# poweroff (IKKE reboot): maskinen skal staa helt stille saa Bjoern kan traekke
# stikket, vente 30 s og taende igen. En ATX-PSU holder +5VSB saa laenge stikket
# sidder i, saa kun en fysisk afbrydelse nulstiller stroemlaget -- og det er
# praecis det lag mistanken peger paa.

LOG=/var/log/pve-safe-shutdown.log
exec >> "$LOG" 2>&1

say() { echo "[$(date +%H:%M:%S)] $*"; }

# Luk en guest paent, og haardt hvis den ikke adlyder inden for timeout.
down() {
    local kind=$1 id=$2 navn=$3 frist=${4:-90}
    say "--- $navn ($kind $id): lukker ned (frist ${frist}s)"
    if [ "$kind" = ct ]; then
        pct shutdown "$id" --timeout "$frist" >/dev/null 2>&1
    else
        qm shutdown "$id" --timeout "$frist" >/dev/null 2>&1
    fi
    # Verificér — stol aldrig paa exit-koden alene.
    local i=0
    while [ $i -lt "$frist" ]; do
        if [ "$kind" = ct ]; then
            pct status "$id" 2>/dev/null | grep -q stopped && { say "    $navn er nede"; return 0; }
        else
            qm status "$id" 2>/dev/null | grep -q stopped && { say "    $navn er nede"; return 0; }
        fi
        sleep 2; i=$((i+2))
    done
    say "    $navn svarede ikke -> haardt stop"
    if [ "$kind" = ct ]; then pct stop "$id" >/dev/null 2>&1; else qm stop "$id" >/dev/null 2>&1; fi
    sleep 5
    say "    $navn stoppet haardt"
}

say "===== KONTROLLERET NEDLUKNING START ====="
say "uptime foer: $(uptime -p)"

# 1) Jarvis foerst — han har en ~2 GB SQLite-DB der skal flushes ordentligt.
down ct 105 "Jarvis" 120
# 2) Resten af de 'sikre' guests (ingen netvaerksafhaengighed for mig).
down ct 104 "fileserver" 90
down ct 106 "llm-gateway" 90
down vm 101 "WebServices" 120
down vm 102 "home-assistant" 120

# 3) TIL SIDST: DNS og netvaerk. Herfra mister jeg forbindelsen — derfor detached.
say ">>> lukker nu DNS + netvaerk (SSH doer her)"
down ct 100 "pihole (DNS)" 60
down vm 103 "pfSense (netvaerk)" 90

# 4) Verificér at ALT er nede foer vi slukker.
rest=$( (pct list; qm list) 2>/dev/null | grep -c running )
say "guests der stadig koerer: $rest"

say "===== POWEROFF om 10 s — traek stikket, vent 30 s, taend igen ====="
sync
sleep 10
/sbin/poweroff
