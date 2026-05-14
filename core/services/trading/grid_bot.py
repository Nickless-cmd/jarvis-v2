"""
Jarvis Grid Trading Bot V2 — Binance Spot
Fase 1: Paper Trading (Testnet)
Multi-pair, re-centering, autocompound, wider spread.
"""
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path

from binance.client import Client
from binance.enums import *

logger = logging.getLogger("jarvis.trading")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
STATE_DIR = Path.home() / ".jarvis-v2" / "state" / "trading"
FEE_RATE_PCT = 0.1  # Binance standard taker-fee

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class GridConfig:
    """Konfiguration for én grid-instans."""
    symbol: str = "BTCUSDT"
    grid_levels: int = 7
    grid_spacing_pct: float = 0.8
    order_size_usdt: float = 12.0
    stop_loss_pct: float = 6.0
    daily_cap_pct: float = 10.0
    re_center_threshold_pct: float = 2.0
    autocompound: bool = True

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


@dataclass
class FeeTracker:
    """Fee-akkumulering."""
    fees_today: float = 0.0
    fees_total: float = 0.0

    def deduct(self, trade_value_usdt: float) -> float:
        fee = trade_value_usdt * (FEE_RATE_PCT / 100)
        self.fees_today += fee
        self.fees_total += fee
        return fee


@dataclass
class GridState:
    """Runtime state for én grid-instans."""
    levels: dict = field(default_factory=dict)
    open_orders: list = field(default_factory=list)
    filled_orders: list = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    trades_today: int = 0
    last_price: float = 0.0
    entry_price: float = 0.0
    starting_value_usdt: float = 0.0
    current_value_usdt: float = 0.0
    max_drawdown_pct: float = 0.0
    peak_value: float = 0.0
    fee_tracker: FeeTracker = field(default_factory=FeeTracker)

    def to_dict(self) -> dict:
        return {
            "levels": self.levels,
            "daily_pnl": round(self.daily_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "trades_today": self.trades_today,
            "last_price": self.last_price,
            "entry_price": self.entry_price,
            "current_value_usdt": round(self.current_value_usdt, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "fees": round(self.fee_tracker.fees_total, 4),
        }


# ---------------------------------------------------------------------------
# GridBotV2
# ---------------------------------------------------------------------------
class GridBotV2:
    """Fælles motor for grid trading. Én instans = én instans af én instans-støtte.

    Håndterer: prishentning, grid-beregning, stop-loss, re-centering,
    autocompound og state persistens.
    """

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        config: Optional[GridConfig] = None,
    ):
        self.config = config or GridConfig()
        self.testnet = testnet
        self._running = True
        self._simulation = False

        if testnet:
            self.client = Client(
                api_key or "", api_secret or "", testnet=True,
            )
        else:
            self.client = Client(api_key, api_secret)

        self.state = GridState()
        STATE_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(
            "GridBotV2 klar | %s | %d grid | %.1f%% spacing | re-center@%.1f%% | autocompound=%s",
            self.config.symbol,
            self.config.grid_levels,
            self.config.grid_spacing_pct,
            self.config.re_center_threshold_pct,
            self.config.autocompound,
        )

    # -----------------------------------------------------------------------
    # Price
    # -----------------------------------------------------------------------
    def get_price(self) -> float:
        ticker = self.client.get_symbol_ticker(symbol=self.config.symbol)
        price = float(ticker["price"])
        self.state.last_price = price
        return price

    def get_precision(self) -> int:
        info = self.client.get_symbol_info(self.config.symbol)
        for filt in info["filters"]:
            if filt["filterType"] == "LOT_SIZE":
                step = float(filt["stepSize"])
                return max(0, -int(f"{step:.10f}".rstrip("0").split(".")[1]) if "." in str(step) else 0)
        return 6

    # -----------------------------------------------------------------------
    # Grid calculation
    # -----------------------------------------------------------------------
    def calculate_grid_levels(self, center_price: float) -> dict:
        half = self.config.grid_levels // 2
        levels = {"buy": [], "sell": []}

        for i in range(1, half + 1):
            pct = i * self.config.grid_spacing_pct / 100
            levels["buy"].append(round(center_price * (1 - pct), 2))
            levels["sell"].append(round(center_price * (1 + pct), 2))

        if self.config.grid_levels % 2 == 1:
            extra = (half + 1) * self.config.grid_spacing_pct / 100
            levels["buy"].append(round(center_price * (1 - extra), 2))

        levels["buy"].sort(reverse=True)
        levels["sell"].sort()
        self.state.levels = levels
        return levels

    def should_re_center(self, current_price: float) -> bool:
        if not self.state.entry_price:
            return False
        drift = abs(current_price - self.state.entry_price) / self.state.entry_price * 100
        return drift >= self.config.re_center_threshold_pct

    def re_center_grid(self, current_price: float):
        logger.info(
            "↻ Re-center %s: $%.2f → $%.2f (drift %.1f%%)",
            self.config.symbol,
            self.state.entry_price,
            current_price,
            abs(current_price - self.state.entry_price) / self.state.entry_price * 100,
        )
        self.state.entry_price = current_price
        self.calculate_grid_levels(current_price)
        self.write_trading_state()

    # -----------------------------------------------------------------------
    # Stop loss & drawdown
    # -----------------------------------------------------------------------
    def check_stop_loss(self, current_price: float) -> bool:
        if self.state.entry_price == 0:
            return False
        loss_pct = (current_price - self.state.entry_price) / self.state.entry_price * 100
        if loss_pct <= -self.config.stop_loss_pct:
            logger.warning("🛑 Stop-loss! %.1f%% (limit %.1f%%)", loss_pct, self.config.stop_loss_pct)
            return True
        return False

    def update_drawdown(self, current_value: float):
        if current_value > self.state.peak_value:
            self.state.peak_value = current_value
        if self.state.peak_value > 0:
            dd = (self.state.peak_value - current_value) / self.state.peak_value * 100
            if dd > self.state.max_drawdown_pct:
                self.state.max_drawdown_pct = round(dd, 2)

    # -----------------------------------------------------------------------
    # Autocompound
    # -----------------------------------------------------------------------
    def apply_autocompound(self, pnl_from_cycle: float):
        if not self.config.autocompound or pnl_from_cycle <= 0:
            return
        boost = pnl_from_cycle * 0.5
        self.config.order_size_usdt += boost
        logger.info("📈 Autocompound: +$%.2f → order_size = $%.2f", boost, self.config.order_size_usdt)

    # -----------------------------------------------------------------------
    # State persistence
    # -----------------------------------------------------------------------
    def write_trading_state(self):
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": self.config.symbol,
            "state": self.state.to_dict(),
            "config": self.config.to_dict(),
        }
        path = STATE_DIR / f"grid_{self.config.symbol.replace('/', '_')}.json"
        with open(path, "w") as f:
            json.dump(entry, f, indent=2)

    # -----------------------------------------------------------------------
    # Run helpers
    # -----------------------------------------------------------------------
    def place_grid_orders(self, levels: dict):
        pass

    def cancel_all_orders(self):
        self.state.open_orders.clear()

    def stop(self):
        self._running = False
        self.cancel_all_orders()
        self.write_trading_state()
        logger.info("⏹️ Bot stoppet — %s", self.config.symbol)

    # -----------------------------------------------------------------------
    # Simulation
    # -----------------------------------------------------------------------
    def run_simulation(self) -> list:
        """Kør én cycle i simulation. Returnér liste af actions."""
        try:
            price = self.get_price()
        except Exception as e:
            logger.error("Kunne ikke hente pris: %s", e)
            return []

        # Første gang — initialisér
        if self.state.entry_price == 0:
            self.state.entry_price = price
            self.state.starting_value_usdt = self.state.current_value_usdt or 200.0
            self.state.peak_value = self.state.starting_value_usdt
            self.calculate_grid_levels(price)
            logger.info("🎯 Init %s @ $%.2f", self.config.symbol, price)
            return [{
                "symbol": self.config.symbol, "action": "init",
                "price": price, "timestamp": datetime.utcnow().isoformat(),
            }]

        # Stop-loss
        if self.check_stop_loss(price):
            self.stop()
            return [{"symbol": self.config.symbol, "action": "stop_loss", "price": price}]

        # Re-center
        if self.should_re_center(price):
            self.re_center_grid(price)
            return [{"symbol": self.config.symbol, "action": "re_center", "price": price}]

        # Simulér grid-actions
        actions = []
        prev_price = self.state.last_price or price
        pnl_this_cycle = 0.0

        # Køb hvis prisen falder gennem et niveau
        for level in self.state.levels.get("buy", []):
            if prev_price >= level > price:
                fee = self.state.fee_tracker.deduct(self.config.order_size_usdt)
                self.state.trades_today += 1
                pnl_this_cycle -= fee
                actions.append({
                    "symbol": self.config.symbol, "action": "buy",
                    "level": level, "price": price,
                    "fee": round(fee, 4),
                    "timestamp": datetime.utcnow().isoformat(),
                })

        # Sælg hvis prisen stiger gennem et niveau
        for level in self.state.levels.get("sell", []):
            if prev_price <= level < price:
                gross = self.config.order_size_usdt
                fee = self.state.fee_tracker.deduct(gross)
                profit = gross * (self.config.grid_spacing_pct / 100) * 0.5
                pnl_this_cycle += profit - fee
                self.state.trades_today += 1
                actions.append({
                    "symbol": self.config.symbol, "action": "sell",
                    "level": level, "price": price,
                    "profit": round(profit, 4), "fee": round(fee, 4),
                    "timestamp": datetime.utcnow().isoformat(),
                })

        # Opdater PnL
        self.state.daily_pnl += pnl_this_cycle
        self.state.total_pnl += pnl_this_cycle
        self.state.current_value_usdt = self.state.starting_value_usdt + self.state.total_pnl

        # Autocompound
        self.apply_autocompound(pnl_this_cycle)

        # Drawdown
        self.update_drawdown(self.state.current_value_usdt)

        # Persistér
        self.write_trading_state()

        return actions

    def run_once(self) -> list:
        """Alias for run_simulation — bruges af loop."""
        return self.run_simulation()


# ---------------------------------------------------------------------------
# Legacy alias
# ---------------------------------------------------------------------------
GridBot = GridBotV2


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
def demo():
    """Demo-kørsel på Binance testnet — 3 cycles."""
    print("=" * 60)
    print(" 🦾 JARVIS GRID BOT V2 — Paper Trading Demo")
    print("=" * 60)

    config = GridConfig(
        grid_levels=7,
        grid_spacing_pct=0.8,
        order_size_usdt=12.0,
        stop_loss_pct=6.0,
        re_center_threshold_pct=2.0,
        autocompound=True,
    )
    bot = GridBotV2(testnet=True, config=config)

    try:
        price = bot.get_price()
        levels = bot.calculate_grid_levels(price)

        print(f"\n📊 {config.symbol}: ${price}")
        print(f"   Grid: {config.grid_levels} niveauer, {config.grid_spacing_pct}% spacing")
        print(f"   Order size: ${config.order_size_usdt}")
        print(f"   Stop-loss: {config.stop_loss_pct}%")
        print(f"   Re-center: ved {config.re_center_threshold_pct}% drift")
        print(f"   Autocompound: {'JA' if config.autocompound else 'NEJ'}")

        print(f"\n🎯 Grid-niveauer omkring ${price}:")
        for lvl in levels.get("buy", []):
            print(f"   🟢 KØB @ ${lvl}")
        print(f"   🟡 MIDT @ ${price}")
        for lvl in levels.get("sell", []):
            print(f"   🔴 SÆLG @ ${lvl}")

        print(f"\n✅ Kører 3 demo-cycles...")
        for i in range(3):
            actions = bot.run_simulation()
            p = bot.get_price()
            print(f"   Cycle {i+1}: price=${p}, {len(actions)} actions")
            for a in actions:
                print(f"      → {a['action']} @ ${a['price']}")

        print(f"\n📈 PnL: daily=${bot.state.daily_pnl:.2f}, total=${bot.state.total_pnl:.2f}")
        print(f"📉 Max drawdown: {bot.state.max_drawdown_pct:.1f}%")
        print(f"💰 Autocompound order_size: ${config.order_size_usdt:.2f}")
        print(f"💸 Fees total: ${bot.state.fee_tracker.fees_total:.4f}")

    finally:
        bot.stop()


# ---------------------------------------------------------------------------
# Continuous run (used by process_spawn)
# ---------------------------------------------------------------------------
def run_continuous():
    """Kør grid-bot i loop hvert 60. sekund indtil stoppet."""
    import signal

    config = GridConfig(
        grid_levels=7,
        grid_spacing_pct=0.8,
        order_size_usdt=12.0,
        stop_loss_pct=6.0,
        re_center_threshold_pct=2.0,
        autocompound=True,
    )
    bot = GridBotV2(testnet=True, config=config)

    def handle_sigterm(signum, frame):
        print("\n⏹️ SIGTERM modtaget — stopper grid-bot...")
        bot.stop()

    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    cycle_count = 0
    interval = 60  # sekunder mellem cycles

    print("=" * 60)
    print(" 🦾 JARVIS GRID BOT V2 — Continuous Paper Trading")
    print("=" * 60)

    try:
        while bot._running:
            cycle_count += 1
            actions = bot.run_simulation()
            price = bot.state.last_price
            print(
                f"  Cycle {cycle_count}: price=${price:.2f}, "
                f"actions={len(actions)}, "
                f"PnL=${bot.state.total_pnl:.2f}, "
                f"trades={bot.state.trades_today}"
            )
            for a in actions:
                print(f"    → {a['action']} @ ${a.get('price', 0):.2f}")

            # Vent (i små bidder så SIGTERM fanges hurtigt)
            for _ in range(interval):
                if not bot._running:
                    break
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏹️ KeyboardInterrupt — stopper grid-bot...")
    finally:
        bot.stop()
        print(f"📈 Final PnL: daily=${bot.state.daily_pnl:.2f}, total=${bot.state.total_pnl:.2f}")
        print(f"📉 Max drawdown: {bot.state.max_drawdown_pct:.1f}%")
        print(f"💸 Fees total: ${bot.state.fee_tracker.fees_total:.4f}")


if __name__ == "__main__":
    import sys
    if "--continuous" in sys.argv or "-c" in sys.argv:
        run_continuous()
    else:
        demo()
