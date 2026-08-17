#!/bin/bash
# Tvinger chrome-sandbox tilbage til setuid-root (4755) EFTER electron-builders egen
# postinst-logik.
#
# Rod (Bjørn 17. aug 2026 — "desk vil ikke starte" efter hver install):
# electron-builders default-postinst afgør sandkasse-tilstand med
#     if ! { [[ -L /proc/self/ns/user ]] && unshare --user true; } ...
# Den test kører som root og UKONFINERET under installationen, så den lykkes på
# Ubuntu 24.04 → else-grenen sætter `chmod 0755`. MEN ved kørsel er Electron-binæren
# i /opt AppArmor-KONFINERET (kernel.apparmor_restrict_unprivileged_userns=1), så den
# kan IKKE bruge user-namespace-sandkassen og kræver SUID-helperen. Med 0755 aborterer
# Electron fatalt FØR vinduet vises ("SUID sandbox helper ... mode 4755") = appen
# "gør ingenting".
#
# afterPack-hooken sætter bittet korrekt i det pakkede output (og .deb'en indeholder
# faktisk -rwsr-xr-x), men postinst kører BAGEFTER og nulstiller det. Derfor skal
# rettelsen ligge her, sidst i postinst.
chmod 4755 '/opt/J.A.R.V.I.S/chrome-sandbox' || true
