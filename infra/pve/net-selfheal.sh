#!/bin/bash
# SELF-HEAL AF MANAGEMENT-ADGANG
#
# Bjoern 20. aug: "det der kan opstaa er jeg skal bytte rundt paa de interne
# netvaerks kabeler fordi det ikk rammer den rigtige usb port"
#
# vmbr1 baerer vaertens management-IP (10.0.0.29). Rammer LAN-kablet en ANDEN
# port end eno1, kommer maskinen op UDEN adgang — og saa skal der skaerm og
# tastatur til (eller AMT, hvis den er sat op).
#
# Denne service koerer EFTER networking og retter netop det: har vmbr1 intet
# link, saa find den port der rent faktisk har LAN-trafik og flyt den ind i
# vmbr1. Kablernes raekkefoelge bliver dermed ligegyldig for at komme IND.
#
# FAIL-SAFE: roerer kun noget hvis vmbr1 er UDEN link. Lykkes intet, efterlader
# den systemet praecis som det var. WAN/DMZ roeres ALDRIG — de kan ikke laase
# nogen ude, og en forkert gaetning der ville lave loops er ikke besvaeret vaerd.

LOG=/var/log/net-selfheal.log
exec >> "$LOG" 2>&1
echo "[$(date '+%F %T')] --- net-selfheal start ---"

has_link() { [ "$(cat /sys/class/net/$1/carrier 2>/dev/null || echo 0)" = "1" ]; }

# Giv langsomme USB-adaptere tid til at forhandle link.
for _ in $(seq 1 15); do has_link vmbr1 && break; sleep 2; done

if has_link vmbr1; then
    echo "vmbr1 har link — ingen indgriben noedvendig"
    exit 0
fi

echo "vmbr1 har INTET link — leder efter LAN (10.0.0.0/24) paa de oevrige porte"

for i in $(ls /sys/class/net | grep -vE '^(lo|vmbr|wlp|veth|tap|fw|bonding)'); do
    # Spring porte over der allerede er slaver i en bro (WAN/DMZ).
    [ -e "/sys/class/net/$i/master" ] && continue
    has_link "$i" || { echo "  $i: intet link"; continue; }

    ip link set "$i" up 2>/dev/null
    # Lyt passivt: ser vi 10.0.0.x-trafik, er det LAN-kablet.
    hits=$(timeout 12 tcpdump -i "$i" -nn -c 20 'arp or (udp and (port 67 or port 68))' 2>/dev/null \
           | grep -cE '(^|[^0-9])10\.0\.0\.[0-9]+')
    echo "  $i: $hits LAN-pakker"

    if [ "${hits:-0}" -ge 2 ]; then
        echo "  -> $i ser ud til at vaere LAN. Flytter den til vmbr1."
        # Tag den ud af enhver bro den maatte sidde i, og læg den i vmbr1.
        ip link set "$i" nomaster 2>/dev/null
        ip link set "$i" master vmbr1 2>/dev/null
        ip link set vmbr1 up 2>/dev/null
        sleep 3
        if has_link vmbr1; then
            echo "  ✅ vmbr1 har link via $i — management-adgang genoprettet"
            echo "     (permanent fix: byt bridge-ports om i /etc/network/interfaces)"
            exit 0
        fi
        echo "  ...gav ikke link, ruller tilbage"
        ip link set "$i" nomaster 2>/dev/null
    fi
done

echo "❌ fandt ingen LAN-port. Brug AMT eller skaerm+tastatur; koer /root/identify_ports.sh"
exit 0
