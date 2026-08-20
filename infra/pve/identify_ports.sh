#!/bin/bash
# HVILKET KABEL SIDDER I HVILKEN PORT?
#
# Bjoern 20. aug: "det der kan opstaa er jeg skal bytte rundt paa de interne
# netvaerks kabeler fordi det ikk rammer den rigtige usb port"
#
# To identiske ASIX AX88179-adaptere kan ikke kendes fra hinanden fysisk. I
# stedet for at GAETTE og saette broerne op forkert, IDENTIFICERER vi hvert
# net FOER vi konfigurerer: lyt passivt paa hver port med link og se hvilke
# IP-subnet der annoncerer sig (ARP + DHCP + broadcast). Saa ved vi praecis
# hvilken port der er WAN, LAN og DMZ — uanset hvilken raekkefoelge kablerne
# sidder i.
#
# HELT PASSIV: sender intet, aendrer ingen config. Kan koeres saa mange gange
# som noedvendigt mens kabler flyttes rundt.

SECS=${1:-12}
echo "=== PORTE MED LINK ==="
for i in $(ls /sys/class/net | grep -vE "^(lo|vmbr|wlp|veth|tap|fw|bonding)"); do
    carrier=$(cat /sys/class/net/$i/carrier 2>/dev/null || echo 0)
    speed=$(cat /sys/class/net/$i/speed 2>/dev/null || echo "?")
    mac=$(cat /sys/class/net/$i/address 2>/dev/null)
    drv=$(basename "$(readlink /sys/class/net/$i/device/driver 2>/dev/null)" 2>/dev/null)
    if [ "$carrier" = "1" ]; then
        echo "  ✅ $i  LINK  ${speed}Mb/s  mac=$mac  driver=$drv"
    else
        echo "  ⬜ $i  intet link       mac=$mac  driver=$drv"
    fi
done

echo
echo "=== LYTTER ${SECS}s PAA HVER PORT MED LINK (passivt) ==="
for i in $(ls /sys/class/net | grep -vE "^(lo|vmbr|wlp|veth|tap|fw|bonding)"); do
    [ "$(cat /sys/class/net/$i/carrier 2>/dev/null)" = "1" ] || continue
    echo "--- $i ---"
    # Sikr at porten er oppe uden at give den en IP (ingen konflikt-risiko).
    ip link set "$i" up 2>/dev/null
    # Fang ARP/DHCP/broadcast og udled hvilke subnet der lever paa kablet.
    timeout "$SECS" tcpdump -i "$i" -nn -c 40 -l \
        'arp or (udp and (port 67 or port 68)) or icmp' 2>/dev/null \
      | grep -oE '([0-9]{1,3}\.){3}[0-9]{1,3}' \
      | awk -F. '{print $1"."$2"."$3".0/24"}' \
      | sort | uniq -c | sort -rn | head -4 \
      | while read n net; do echo "    $net   ($n pakker)"; done
    echo "    (tomt = ingen trafik hoert — kabel i? modparten stille?)"
done

echo
echo "=== FORVENTEDE NET (fra Z390) ==="
echo "  WAN : 100.75.136.0/24   -> skal paa vmbr0"
echo "  LAN : 10.0.0.0/24       -> skal paa vmbr1"
echo "  DMZ : 192.168.50.0/24   -> skal paa vmbr2"
