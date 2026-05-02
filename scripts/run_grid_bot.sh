#!/usr/bin/env bash
# Jarvis Grid Bot — continuous simulation loop
# Spawned via process_spawn, supervised by JarvisX
set -euo pipefail

cd /media/projects/jarvis-v2

CYCLE_INTERVAL="${GRID_BOT_INTERVAL:-30}"  # seconds between cycles, default 30

echo "=== Grid Bot starting (interval: ${CYCLE_INTERVAL}s) ==="

# Use the 'ai' conda env where binance + other deps are installed.
# When spawned via process_supervisor the parent's PATH may not have
# conda activated, so we call the absolute path directly.
PYTHON_BIN="${PYTHON_BIN:-/opt/conda/envs/ai/bin/python3.11}"

"$PYTHON_BIN" -c "
import time, sys, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
from core.services.trading.grid_bot import GridBot

bot = GridBot(testnet=True, simulation=True, sim_start_usdt=200.0)
bot._running = True
print(f'Grid Bot initialized — simulation mode, 200 USDT start', flush=True)

cycle = 0
while bot._running:
    cycle += 1
    try:
        actions = bot.run_simulation()
        print(f'Cycle {cycle}: {len(actions)} actions', flush=True)
    except Exception as e:
        print(f'Cycle {cycle} ERROR: {e}', flush=True)
        import traceback
        traceback.print_exc()
    time.sleep(${CYCLE_INTERVAL})
"