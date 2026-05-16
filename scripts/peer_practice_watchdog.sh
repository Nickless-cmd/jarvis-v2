#!/usr/bin/env bash
# scripts/peer_practice_watchdog.sh
# Spawn én process per peer + restart on crash.
# Total: 6 peer-processer kører i 7 dage = 168 timer.
#
# Usage:
#   ./scripts/peer_practice_watchdog.sh            # foreground
#   nohup ./scripts/peer_practice_watchdog.sh > ~/.jarvis-v2/logs/watchdog-master.log 2>&1 &
#
# Stop:
#   pkill -f peer_practice_watchdog.sh && pkill -f peer_practice_runner
#
# Spec: docs/superpowers/specs/2026-05-16-interlanguage-validation-design.md

set -u

PEERS=(claude claude_jp glm glm_jp ollama_local random)
SEED_FLAGS=("" "--use-seed" "" "--use-seed" "" "")
PYTHON=/opt/conda/envs/ai/bin/python
REPO=/media/projects/jarvis-v2
LOG_DIR="${HOME}/.jarvis-v2/logs/interlanguage_validation"
mkdir -p "$LOG_DIR"

run_peer() {
  local peer="$1"
  local flag="$2"
  local logfile="$LOG_DIR/${peer}.log"
  echo "[watchdog] launching peer=$peer flag=$flag log=$logfile"
  while true; do
    {
      echo "[watchdog] starting peer=$peer at $(date -Iseconds)"
      cd "$REPO" && "$PYTHON" scripts/peer_practice_runner.py --peer "$peer" --hours 168 $flag
      echo "[watchdog] peer=$peer exited rc=$? — sleeping 60s before restart"
    } >> "$logfile" 2>&1
    sleep 60
  done
}

for i in "${!PEERS[@]}"; do
  run_peer "${PEERS[$i]}" "${SEED_FLAGS[$i]}" &
done

wait
