"""
Jarvis Grid Trading Bot — Binance Spot
Fase 1: Paper Trading (Testnet)
"""

from binance.client import Client
from binance.enums import *
import json
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("jarvis.trading")


@dataclass
class GridConfig:
    """Konfiguration for grid trading."""
    symbol: str = "BTCUSDT"
    grid_levels: int = 5
    grid_spacing_pct: float = 1.0  # % mellem hvert niveau
    order_size_usdt: float = 10.0  # pr. ordre
    stop_loss_pct: float = 5.0
    daily_cap_pct: float = 10.0


@dataclass
class FeeTracker:
    """Fee-akkumulering per handel og total."""
    fees_today: float = 0.0
    fees_total: float = 0.0
    fee_rate_pct: float = 0.1  # Binance standard taker fee

    def deduct(self, trade_value_usdt: float) -> float:
        """Beregn og akkumulér fee for et trade. Returnér fee-beløb."""
        fee = trade_value_usdt * (self.fee_rate_pct / 100)
        self.fees_today += fee
        self.fees_total += fee
        return fee


@dataclass
class GridState:
    """Nuværende state for grid botten."""
    levels: dict = field(default_factory=dict)
    open_orders: list = field(default_factory=list)
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    trades_today: int = 0
    last_price: float = 0.0
    entry_price: float = 0.0
    starting_value_usdt: float = 0.0
    max_drawdown_pct: float = 0.0
    fee_tracker: FeeTracker = field(default_factory=FeeTracker)


class GridBot:
    """Simpel grid trading bot til Binance."""

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        config: Optional[GridConfig] = None,
        simulation: bool = False,
        sim_start_usdt: float = 200.0,
    ):
        self.config = config or GridConfig()
        self.simulation = simulation
        # Altid brug Binance client til pris-hentning (selv i simulation)
        self.client = Client(api_key, api_secret)
        if testnet or simulation:
            self.client.API_URL = "https://testnet.binance.vision/api"
            logger.info("🔬 KØRER PÅ TESTNET — ingen rigtige penge!")

        if simulation:
            logger.info(f"🔬 SIMULATION MODE — start balance: {sim_start_usdt} USDT")
            self.sim_balance = {
                "USDT": sim_start_usdt,
                self.config.symbol.replace("USDT", ""): 0.0,
            }
            self.sim_trades = []

        self.testnet = testnet
        self.state = GridState()
        self._running = False

        # State-fil sti — atomic write destination for dashboard
        self._state_file = Path.home() / ".jarvis-v2" / "state" / "trading_state.json"

    def write_trading_state(self):
        """Atomic write af trading state til JSON-fil for dashboard-consumption."""
        try:
            price = self.state.last_price or self.get_price()
        except Exception:
            price = self.state.last_price or 0.0

        btc_asset = self.config.symbol.replace("USDT", "")

        if self.simulation:
            usdt_balance = round(self.sim_balance.get("USDT", 0.0), 2)
            asset_balance = round(self.sim_balance.get(btc_asset, 0.0), 8)
        else:
            try:
                usdt_balance = round(self.get_balance("USDT"), 2)
                asset_balance = round(self.get_balance(btc_asset), 8)
            except Exception:
                usdt_balance = 0.0
                asset_balance = 0.0

        total_value = round(usdt_balance + (asset_balance * price), 2)
        starting_value = self.state.starting_value_usdt or total_value

        # Drawdown
        if starting_value > 0:
            current_dd = ((starting_value - total_value) / starting_value) * 100
        else:
            current_dd = 0.0
        self.state.max_drawdown_pct = max(self.state.max_drawdown_pct, current_dd)

        # Status
        if not self._running and self.state.trades_today == 0:
            status = "inactive"
        elif self._running:
            status = "active"
        else:
            status = "stopped"

        state_dict = {
            "status": status,
            "mode": "simulation" if self.simulation else ("testnet" if self.testnet else "live"),
            "symbol": self.config.symbol,
            "config": {
                "grid_levels": self.config.grid_levels,
                "grid_spacing_pct": self.config.grid_spacing_pct,
                "order_size_usdt": self.config.order_size_usdt,
                "stop_loss_pct": self.config.stop_loss_pct,
            },
            "capital": {
                "usdt": usdt_balance,
                "asset": asset_balance,
                "asset_symbol": btc_asset,
                "total_value_usdt": total_value,
                "starting_value_usdt": starting_value,
            },
            "pnl": {
                "realized_today": round(self.state.daily_pnl, 4),
                "realized_total": round(self.state.total_pnl, 4),
                "unrealized": round((asset_balance * price) - (asset_balance * (self.state.entry_price or price)), 4),
                "fees_today": round(self.state.fee_tracker.fees_today, 4),
                "fees_total": round(self.state.fee_tracker.fees_total, 4),
            },
            "drawdown": {
                "current_pct": round(current_dd, 2),
                "max_pct_today": round(self.state.max_drawdown_pct, 2),
                "cap_pct": self.config.stop_loss_pct,
            },
            "trades_today": self.state.trades_today,
            "open_orders": [
                {
                    "id": o.get("id", "?"),
                    "side": o.get("side", "?"),
                    "price": o.get("price", 0),
                    "quantity": o.get("quantity", 0),
                    "placed_at": o.get("placed_at", ""),
                }
                for o in self.state.open_orders
            ],
            "last_price": price,
            "recent_trades": [
                {
                    "type": t.get("type", "?"),
                    "price": t.get("price", 0),
                    "qty": t.get("qty", 0),
                    "profit_usdt": t.get("profit_usdt", 0),
                    "timestamp": t.get("timestamp", ""),
                }
                for t in (self.sim_trades[-20:] if self.simulation else self.state.open_orders[-20:])
            ],
            "last_updated": datetime.now().isoformat(),
        }

        # Atomic write: tmp → replace
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(state_dict, indent=2))
        tmp.replace(self._state_file)
        logger.debug(f"📊 State skrevet: {self._state_file}")

    def get_price(self) -> float:
        """Hent nuværende pris."""
        ticker = self.client.get_symbol_ticker(symbol=self.config.symbol)
        price = float(ticker["price"])
        self.state.last_price = price
        return price

    def get_balance(self, asset: str = "USDT") -> float:
        """Hent balance for et asset."""
        if self.simulation:
            return round(self.sim_balance.get(asset, 0.0), 8)
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance["free"])
        except Exception:
            return 0.0

    def calculate_grid_levels(self, center_price: float) -> list[float]:
        """Beregn grid-prisniveauer omkring center_price."""
        levels = []
        for i in range(-self.config.grid_levels, self.config.grid_levels + 1):
            price = center_price * (1 + (i * self.config.grid_spacing_pct / 100))
            levels.append(round(price, 2))
        levels.sort()
        return levels

    def place_buy_order(self, price: float) -> Optional[str]:
        """Placer en limit buy order."""
        quantity = round(self.config.order_size_usdt / price, 6)
        if quantity * price < 10:  # Binance minimum ~$10
            return None

        try:
            order = self.client.order_limit_buy(
                symbol=self.config.symbol,
                quantity=quantity,
                price=str(price),
            )
            logger.info(f"📈 BUY: {quantity} @ ${price} | ID: {order['orderId']}")
            return order["orderId"]
        except Exception as e:
            logger.error(f"❌ BUY fejlede: {e}")
            return None

    def place_sell_order(self, price: float, quantity: float) -> Optional[str]:
        """Placer en limit sell order."""
        if quantity * price < 10:
            return None

        try:
            order = self.client.order_limit_sell(
                symbol=self.config.symbol,
                quantity=round(quantity, 6),
                price=str(price),
            )
            logger.info(f"📉 SELL: {quantity} @ ${price} | ID: {order['orderId']}")
            return order["orderId"]
        except Exception as e:
            logger.error(f"❌ SELL fejlede: {e}")
            return None

    def cancel_all_orders(self) -> int:
        """Annullér alle åbne ordrer."""
        try:
            result = self.client.cancel_open_orders(symbol=self.config.symbol)
            cancelled = len(result) if isinstance(result, list) else 0
            logger.info(f"🚫 Annullerede {cancelled} ordrer")
            return cancelled
        except Exception as e:
            logger.error(f"❌ Cancel fejlede: {e}")
            return 0

    def status(self) -> dict:
        """Returnér nuværende status."""
        try:
            price = self.get_price()
        except Exception as e:
            price = self.state.last_price
            logger.warning(f"Kunne ikke hente pris: {e}")

        if self.simulation:
            btc_asset = self.config.symbol.replace("USDT", "")
            usdt_balance = round(self.sim_balance.get("USDT", 0.0), 2)
            btc_balance = round(self.sim_balance.get(btc_asset, 0.0), 8)
            total_value = round(usdt_balance + (btc_balance * price), 2)
        else:
            try:
                usdt_balance = self.get_balance("USDT")
                btc_balance = self.get_balance(self.config.symbol.replace("USDT", ""))
            except Exception:
                usdt_balance = 0
                btc_balance = 0
            total_value = round(usdt_balance + (btc_balance * price), 2)

        return {
            "symbol": self.config.symbol,
            "price": price,
            "usdt_balance": usdt_balance,
            "btc_balance": btc_balance,
            "total_value_usdt": total_value,
            "daily_pnl": round(self.state.daily_pnl, 4),
            "total_pnl": round(self.state.total_pnl, 4),
            "trades_today": self.state.trades_today,
            "simulation": self.simulation,
            "testnet": self.testnet or self.simulation,
            "timestamp": datetime.now().isoformat(),
        }

    def run_once(self):
        """En enkelt cyklus af grid-strategien."""
        price = self.get_price()
        self.state.last_price = price

        # Første gang: opsæt grid
        if not self.state.levels:
            self.state.entry_price = price
            if self.state.starting_value_usdt == 0:
                self.state.starting_value_usdt = self.get_balance("USDT") or 200.0
            self.state.levels = {
                p: {"buy_order": None, "sell_order": None, "filled": False}
                for p in self.calculate_grid_levels(price)
            }
            logger.info(f"🎯 Grid sat op omkring ${price}")
            logger.info(f"   Niveauer: {list(self.state.levels.keys())}")

        # Tjek stop-loss
        if self.state.entry_price > 0:
            drawdown = (price - self.state.entry_price) / self.state.entry_price * 100
            if drawdown < -self.config.stop_loss_pct:
                logger.critical(f"🛑 STOP-LOSS triggered! -{abs(drawdown):.2f}%")
                self.cancel_all_orders()
                self._running = False
                self.write_trading_state()
                return

        # Placer manglende ordrer
        for level_price, level_state in self.state.levels.items():
            if level_state["filled"]:
                continue

            if price > level_price and not level_state["buy_order"]:
                # Prisen er over dette niveau → skal købe
                order_id = self.place_buy_order(level_price)
                if order_id:
                    level_state["buy_order"] = order_id

            elif price < level_price and level_state["buy_order"] and not level_state["sell_order"]:
                # Prisen er under → vi har købt, nu skal vi sælge
                quantity = self.config.order_size_usdt / level_price
                order_id = self.place_sell_order(
                    level_price * (1 + self.config.grid_spacing_pct / 100),
                    quantity,
                )
                if order_id:
                    level_state["sell_order"] = order_id
                    level_state["filled"] = True
                    gross_profit = self.config.order_size_usdt * self.config.grid_spacing_pct / 100
                    # Fee-deduction på både køb og salg
                    buy_fee = self.state.fee_tracker.deduct(self.config.order_size_usdt)
                    sell_fee = self.state.fee_tracker.deduct(self.config.order_size_usdt * (1 + self.config.grid_spacing_pct / 100))
                    net_profit = gross_profit - buy_fee - sell_fee
                    self.state.total_pnl += net_profit
                    self.state.daily_pnl += net_profit
                    self.state.trades_today += 1

        self._running = True
        self.write_trading_state()

    def run_simulation(self):
        """Simuleringstilstand: hent live-pris, beregn handler med virtual balance-tracking."""
        price = self.get_price()
        self.state.last_price = price

        if not self.state.levels:
            self.state.entry_price = price
            # Gem starting value ved første cyklus
            if self.state.starting_value_usdt == 0:
                self.state.starting_value_usdt = self.sim_balance["USDT"]
            self.state.levels = {
                p: {"buy_order": None, "sell_order": None, "filled": False, "bought_at": None}
                for p in self.calculate_grid_levels(price)
            }
            logger.info(f"🎯 Grid sat op omkring ${price}")
            logger.info(f"   Niveauer: {list(self.state.levels.keys())}")
            logger.info(f"   Start-balance: {self.sim_balance['USDT']:.2f} USDT")
            self.write_trading_state()

        # Stop-loss check
        if self.state.entry_price > 0:
            drawdown = (price - self.state.entry_price) / self.state.entry_price * 100
            if drawdown < -self.config.stop_loss_pct:
                logger.critical(f"🛑 STOP-LOSS triggered! -{abs(drawdown):.2f}% ved ${price}")
                self._running = False
                self.write_trading_state()
                return

        # Tjek hvert grid-niveau for handler
        actions = []
        btc_asset = self.config.symbol.replace("USDT", "")

        for level_price, level_state in sorted(self.state.levels.items()):
            if price <= level_price and not level_state["filled"] and not level_state["buy_order"]:
                # Køb-signal — tjek om vi har råd
                cost = self.config.order_size_usdt
                if self.sim_balance["USDT"] >= cost:
                    btc_qty = cost / level_price
                    # Fee på køb: vi trækker fee fra BTC vi modtager
                    buy_fee = self.state.fee_tracker.deduct(cost)
                    btc_qty_after_fee = btc_qty * (1 - self.state.fee_tracker.fee_rate_pct / 100)
                    self.sim_balance["USDT"] -= cost
                    self.sim_balance[btc_asset] += btc_qty_after_fee
                    level_state["buy_order"] = True
                    level_state["bought_at"] = level_price
                    self.sim_trades.append({
                        "type": "BUY", "price": level_price, "qty": btc_qty_after_fee,
                        "cost_usdt": cost, "fee_usdt": buy_fee,
                        "timestamp": datetime.now().isoformat()
                    })
                    actions.append(
                        f"📈 SIM-KØB: {btc_qty_after_fee:.6f} BTC @ ${level_price:.2f} "
                        f"(${cost:.2f}, fee: ${buy_fee:.4f}) — balance: {self.sim_balance['USDT']:.2f} USDT"
                    )
                    logger.info(actions[-1])
                else:
                    logger.debug(f"⏭️ Skip køb @ ${level_price:.2f} — insufficient USDT ({self.sim_balance['USDT']:.2f})")

            elif price > level_price and level_state["buy_order"] and not level_state["sell_order"]:
                # Sælg-signal
                btc_asset_key = btc_asset
                btc_available = self.sim_balance.get(btc_asset_key, 0.0)
                sell_price = level_price * (1 + self.config.grid_spacing_pct / 100)

                if btc_available > 0:
                    # Sælg den mængde vi købte ved dette niveau
                    buy_cost = self.config.order_size_usdt
                    btc_qty = buy_cost / level_state.get("bought_at", level_price)
                    btc_qty = min(btc_qty, btc_available)
                    revenue = btc_qty * sell_price
                    # Fee på salg: vi trækker fee fra revenue
                    sell_fee = self.state.fee_tracker.deduct(revenue)
                    net_revenue = revenue - sell_fee
                    profit = net_revenue - (btc_qty * level_state.get("bought_at", level_price))

                    self.sim_balance[btc_asset_key] -= btc_qty
                    self.sim_balance["USDT"] += net_revenue
                    level_state["sell_order"] = True
                    level_state["filled"] = True
                    self.state.total_pnl += profit
                    self.state.daily_pnl += profit
                    self.state.trades_today += 1
                    self.sim_trades.append({
                        "type": "SELL", "price": sell_price, "qty": btc_qty,
                        "revenue_usdt": net_revenue, "profit_usdt": profit,
                        "fee_usdt": sell_fee,
                        "timestamp": datetime.now().isoformat()
                    })
                    actions.append(
                        f"📉 SIM-SÆLG: {btc_qty:.6f} BTC @ ${sell_price:.2f} "
                        f"— profit: ${profit:.4f} (fee: ${sell_fee:.4f}) — balance: {self.sim_balance['USDT']:.2f} USDT"
                    )
                    logger.info(actions[-1])

        if not actions:
            logger.debug(f"💤 Ingen handler — pris: ${price}")

        self.write_trading_state()
        self._running = True
        return actions

    def stop(self):
        """Stop botten og ryd op."""
        self._running = False
        self.cancel_all_orders()
        self.write_trading_state()
        logger.info("⏹️ Bot stoppet — alle ordrer annulleret")


def demo():
    """Demo-kørsel på testnet (ingenting handles)."""
    print("=" * 60)
    print("   🦾 JARVIS GRID BOT — Paper Trading Demo")
    print("=" * 60)

    # Testnet — ingen nøgler nødvendige
    bot = GridBot(testnet=True)

    try:
        # Vis priser
        price = bot.get_price()
        print(f"\n📊 {bot.config.symbol}: ${price}")
        print(f"   Grid: {bot.config.grid_levels} niveauer, {bot.config.grid_spacing_pct}% spacing")
        print(f"   Order size: ${bot.config.order_size_usdt}")
        print(f"   Stop-loss: {bot.config.stop_loss_pct}%")

        # Beregn grid
        levels = bot.calculate_grid_levels(price)
        print(f"\n🎯 Grid-niveauer omkring ${price}:")
        for lvl in levels:
            direction = "🟢 KØB" if lvl < price else ("🔴 SÆLG" if lvl > price else "🟡 MIDT")
            print(f"   {direction} @ ${lvl}")

        print(f"\n✅ Bot klar til at køre. Kald bot.run_once() for at starte.")
        print("   (Ingen handler udført — dette er en demo)")

    except Exception as e:
        print(f"\n⚠️ Kunne ikke forbinde til Binance testnet: {e}")
        print("   Tjek internetforbindelse.")
        print("   Bot-koden er klar og kan køre når forbindelsen er oppe.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    demo()