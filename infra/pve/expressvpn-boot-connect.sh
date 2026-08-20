#!/bin/sh
# Forbinder ExpressVPN ved boot.
#
# USA (ikke Danmark) siden 20-08-2026: cheap-lanens account2 skal have BAADE
# en anden IP OG en anden geografi end account1 — ellers kan providere se dem
# som samme kilde og blokere. Scriptet stod foer paa "denmark", og da
# `expressvpnctl set region` IKKE overlever en genstart (klienten falder
# tilbage til smart location = naermeste server = Danmark), var dette scriptet
# den reelle aarsag til at tunnellen altid endte i Danmark.
#
# Verificeret ved genstart 20-08: uden dette fix tog det ~90 s foer tunnellen
# kom op, og den kom op i DANMARK.
REGION=usa-new-york

expressvpnctl background enable >/dev/null 2>&1
expressvpnctl set autoconnect true >/dev/null 2>&1

for i in $(seq 1 45); do
    s=$(expressvpnctl get connectionstate 2>/dev/null)
    r=$(expressvpnctl get region 2>/dev/null)
    # Godkend KUN naar den baade er forbundet OG i den rigtige region —
    # den gamle version tjekkede kun "Connected" og accepterede derfor
    # en dansk tunnel som succes.
    if [ "$s" = "Connected" ] && [ "$r" = "$REGION" ]; then
        logger -t expressvpn-boot "forbundet til $REGION efter $((i * 5))s"
        exit 0
    fi
    # Kald KUN connect naar den rent faktisk er nede. Den gamle version
    # fyrede `connect` hver 5. sekund — ogsaa midt i et igangvaerende
    # handshake — og afbroed dermed sit eget forsoeg. USA-serveren skal
    # bruge laengere tid end den danske, saa det kostede reelt minutter.
    if [ "$s" != "Connecting" ]; then
        expressvpnctl connect "$REGION" >/dev/null 2>&1
    fi
    sleep 5
done

logger -t expressvpn-boot "ADVARSEL: naaede ikke $REGION inden for 225s (state=$s region=$r)"
exit 0
