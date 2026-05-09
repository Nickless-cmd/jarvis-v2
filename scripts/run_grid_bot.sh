# Jarvis Grid Bot — continuous simulation loop
# Spawned via process_spawn, supervised by JarvisX
set -euo pipefail

cd /media/projects/jarvis-v2

CYCLE_INTERVAL="${GRID_BOT_INTERVAL:-30}"  # seconds between cycles, default 30

echo "=== Grid Bot V2 starting (interval: ${CYCLE_INTERVAL}s) ==="

PYTHON_BIN="${PYTHON_BIN:-/opt/conda/envs/ai/bin/python3.11}"

"$PYTHON_BIN" -c "
CYCLE_INTERVAL = ${CYCLE_INTERVAL}
import time, sys, logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
from core.services.trading.grid_bot import GridBotV2, GridConfig

# Multi-pair setup: BTC, ETH, SOL
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
bots = {}
for sym in SYMBOLS:
    cfg = GridConfig(
        symbol=sym,
        grid_levels=7,
        grid_spacing_pct=0.8,
        order_size_usdt=12.0,
        stop_loss_pct=6.0,
        re_center_threshold_pct=2.0,
        autocompound=True,
    )
    bot = GridBotV2(testnet=True, config=cfg)
    bot._simulation = True
    bot.state.current_value_usdt = 200.0  # 200 USDT pr. pair
    bot._running = True
    bots[sym] = bot
    print(f'{sym}: Init — 200 USDT, {cfg.grid_levels} levels, {cfg.grid_spacing_pct}% spacing', flush=True)

total_start = len(SYMBOLS) * 200
print(f'=== {len(SYMBOLS)} pairs, {total_start} USDT total, interval {CYCLE_INTERVAL}s ===', flush=True)

cycle = 0
while any(b._running for b in bots.values()):
    cycle += 1
    for sym, bot in bots.items():
        if not bot._running:
            continue
        try:
            actions = bot.run_once()
            if actions:
                pnl = round(bot.state.total_pnl, 2)
                val = round(bot.state.current_value_usdt, 2)
                print(f'Cycle {cycle} | {sym}: {len(actions)} actions | PnL={pnl} | Value={val}', flush=True)
        except Exception as e:
            print(f'Cycle {cycle} | {sym}: ERROR: {e}', flush=True)
            import traceback; traceback.print_exc()
    time.sleep(${CYCLE_INTERVAL})

print('=== All bots stopped ===', flush=True)
"
