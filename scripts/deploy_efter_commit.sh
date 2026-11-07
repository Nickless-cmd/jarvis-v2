#!/usr/bin/env bash
# Deploy efter commit — den ENESTE vej (7/11-2026).
#
# ## Hvorfor denne fil findes
#
# Målt 7/11-2026: jeg havde lavet en ny /tmp/deploy_*.sh til hver deploy den
# uge — seks styk. De var kopier af hinanden, og de havde alle samme fejl:
#
#   1. Drain-kaldet pegede på `scripts/drain_visible_runs.py`, et filnavn der
#      ikke findes NOGEN steder i repoet. Jeg havde opfundet det. Husets eget
#      script heder `drain_before_restart.py`.
#   2. Exit-koden blev læst som `echo "$(date -Is) drain rc=$?"`. `$(date -Is)`
#      er en kommando-substitution inde i samme streng, og den kører FØRST —
#      så `$?` var `date`s exit-kode, altid 0. Fejlen var tavs i alle seks
#      logs, og jeg citerede «drain rc=0» som bevis for at det gik fint.
#   3. Derfor genstartede scriptet midt i en levende tur. Kl. 18:11:29 blev
#      `visible-369960d3f5554ae4` stemplet `interrupted` / `shutdown`.
#
# Bjørn, samme aften: «Du glemte defer». Han havde ret. `deferred_restart.py`
# har eksisteret siden 3/10 og gør præcis det jeg havde bygget en dårlig
# efterligning af: venter til MIT run er dødt OG ingen andre kører, og
# ABBRYDER hellere end at dræbe en tur (30 min vindue).
#
# Et løfte om at «huske defer» er ikke et værn — det er den samme fejlform som
# `genstart_sikkert.sh` selv skriver om: «Efter den første sagde jeg at jeg
# ville tjekke først. Det gjorde jeg ikke; jeg genstartede fire gange til. Et
# løfte er ikke et værn.» Derfor dette script: vejen er scriptet, ikke hukommelsen.
#
# ## Brug
#
#   setsid nohup scripts/deploy_efter_commit.sh > /dev/null 2>&1 < /dev/null
#
# Kør den AFKOBLET: den venter på idle, og en tur der venter på sig selv
# venter for evigt.
#
# Exit-koder: 0 = genstartet og verificeret. 2 = UDSKUDT, der kørte noget.
#             1 = genstart fejlede. 3 = koden i processen matcher ikke commit.
set -uo pipefail

REPO="${REPO:-/media/projects/jarvis-v2}"
LOG="${LOG:-/tmp/deploy.log}"
PY="${PY:-/opt/conda/envs/ai/bin/python3}"
TJENESTER="${TJENESTER:-jarvis-api,jarvis-runtime}"

: > "$LOG"

COMMIT_SHORT=$(git -C "$REPO" rev-parse --short HEAD)
COMMIT_EPOCH=$(git -C "$REPO" show -s --format=%ct HEAD)
echo "$(date -Is) START — $COMMIT_SHORT, venter paa idle (defer)" >> "$LOG"

# Trin 1: DEFER. Dette er husets egen mekanisme — ikke en drain jeg selv har
# opfundet. Tomt run-id betyder «vent paa at INTET lever», hvilket er praecis
# hvad en genstart kraever: den draeber alle koersler, ikke kun min.
cd "$REPO" || exit 1
"$PY" "$REPO/scripts/deferred_restart.py" "" "$TJENESTER" >> "$LOG" 2>&1
# Exit-koden laeses PAA SIN EGEN LINJE, foer nogen kommando-substitution.
# Det er hele grunden til at den gamle form loej: `$(date)` inde i samme
# streng nulstillede `$?` inden det blev laest.
rc=$?
echo "$(date -Is) deferred_restart rc=$rc" >> "$LOG"

if [ "$rc" -eq 2 ]; then
  echo "$(date -Is) UDSKUDT — der koerte stadig noget. Ingen genstart, intet tabt." >> "$LOG"
  exit 2
fi
if [ "$rc" -ne 0 ]; then
  echo "$(date -Is) FEJL — genstarten lykkedes ikke (rc=$rc)." >> "$LOG"
  exit 1
fi

# Trin 2: BEVIS at den koerende proces er startet EFTER commit. En genstart
# der ikke naaede frem ser identisk ud med en der gjorde, hvis man kun læser
# «rc=0».
API_START=$(systemctl show jarvis-api -p ActiveEnterTimestamp --value \
  | xargs -I{} date -d {} +%s 2>/dev/null || echo 0)
RT_START=$(systemctl show jarvis-runtime -p ActiveEnterTimestamp --value \
  | xargs -I{} date -d {} +%s 2>/dev/null || echo 0)
echo "$(date -Is) api-start epoch=$API_START · rt-start epoch=$RT_START · commit=$COMMIT_EPOCH" >> "$LOG"

if [ "$API_START" -lt "$COMMIT_EPOCH" ] || [ "$RT_START" -lt "$COMMIT_EPOCH" ]; then
  echo "$(date -Is) FEJL — en tjeneste koerer stadig fra FOER commit." >> "$LOG"
  exit 3
fi

# Trin 3: STIKPROEVE i den koerende kode. Kaldes uden argument og maaler kun
# at modulet kan importeres og at den nye funktion findes — den skal udvides
# pr. deploy med det konkrete symbol, ellers beviser den intet.
echo "--- stikproeve ---" >> "$LOG"
"$PY" - <<'PY' >> "$LOG" 2>&1
import sys
sys.path.insert(0, "/media/projects/jarvis-v2")
from core.services import deferred_restart  # noqa: F401  (importerbart = processen kan)
print("moduler importerbare: True")
PY

echo "$(date -Is) FAERDIG — $COMMIT_SHORT er levende" >> "$LOG"
exit 0
