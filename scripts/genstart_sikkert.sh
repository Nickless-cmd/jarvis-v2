#!/usr/bin/env bash
# Genstart en jarvis-unit — men kun når der ikke kører noget.
#
# Baggrund (13/9-2026): tre af Bjørns kørsler døde af `api-nedlukning` på én
# dag, alle fordi jeg genstartede midt i dem. Den tredje havde preview'et
# «Forsæt» — altså præcis den besked han skriver NÅR en kørsel er død.
#
# Efter den første sagde jeg at jeg ville tjekke først. Det gjorde jeg ikke;
# jeg genstartede fire gange til. Et løfte er ikke et værn.
#
# Brug:  scripts/genstart_sikkert.sh jarvis-api [jarvis-runtime ...]
#        VENT=0 scripts/genstart_sikkert.sh ...   # spring ventetiden over
set -euo pipefail

VAERT="${VAERT:-bs@10.0.0.39}"
ROD="${ROD:-/media/projects/jarvis-v2}"
MAKS_VENT="${MAKS_VENT:-180}"
tvunget=0

aktive() {
  ssh "$VAERT" "cd $ROD && /opt/conda/envs/ai/bin/python - <<'PY'
import sqlite3, pathlib
c = sqlite3.connect(str(pathlib.Path.home()/'.jarvis-v2'/'state'/'jarvis.db'))
rows = c.execute(
    \"SELECT run_id, substr(text_preview,1,60) FROM visible_runs \"
    \"WHERE status='running' AND (finished_at IS NULL OR finished_at='')\"
).fetchall()
for r in rows:
    print(f'{r[0]}\t{r[1] or \"\"}')
PY" 2>/dev/null
}

echo "tjekker for aktive kørsler…"
ventet=0
while true; do
  ud="$(aktive || true)"
  [ -z "$ud" ] && break
  antal=$(printf '%s\n' "$ud" | grep -c . || true)
  echo "  $antal kørsel/kørsler i gang:"
  printf '%s\n' "$ud" | sed 's/^/    /'
  if [ "${VENT:-1}" = "0" ]; then
    echo "  ⚠ VENT=0 — genstarter MIDT I $antal kørsel/kørsler."
    echo "  ⚠ De bliver stemplet 'api-nedlukning'. Det er dét der får Bjørn"
    echo "  ⚠ til at skrive «Forsæt»."
    tvunget=1
    break
  fi
  if [ "$ventet" -ge "$MAKS_VENT" ]; then
    echo "  ventede ${MAKS_VENT}s. Kør igen, eller sæt VENT=0 for at genstarte alligevel." >&2
    exit 1
  fi
  sleep 5
  ventet=$((ventet + 5))
done

# Linjen herunder loej foer: den stod UBETINGET efter loekken, saa en
# VENT=0-overstyring skrev baade «genstarter alligevel» OG «ingen aktive
# koersler» i samme koersel. En besked der siger noget andet end det der skete,
# er praecis den fejlklasse hele dagen gik med.
if [ "${tvunget:-0}" = "1" ]; then
  echo "genstarter TRODS aktive kørsler: $*"
else
  echo "ingen aktive kørsler — genstarter: $*"
fi
ssh "$VAERT" "sudo systemctl restart $*"
sleep 8
ssh "$VAERT" "systemctl is-active $*"
