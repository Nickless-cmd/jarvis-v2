# `core.services.trading` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/trading/__init__.py`

_(no top-level classes or functions)_

## `core/services/trading/grid_bot.py`
_Jarvis Grid Trading Bot V2 — Binance Spot_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GridConfig` | `` | Konfiguration for én grid-instans. | [src](../../../core/services/trading/grid_bot.py#L29) |
| method | `GridConfig.to_dict` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L40) |
| class | `FeeTracker` | `` | Fee-akkumulering. | [src](../../../core/services/trading/grid_bot.py#L45) |
| method | `FeeTracker.deduct` | `(self, trade_value_usdt)` | — | [src](../../../core/services/trading/grid_bot.py#L50) |
| class | `GridState` | `` | Runtime state for én grid-instans. | [src](../../../core/services/trading/grid_bot.py#L58) |
| method | `GridState.to_dict` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L74) |
| class | `GridBotV2` | `` | Fælles motor for grid trading. Én instans = én instans af én instans-støtte. | [src](../../../core/services/trading/grid_bot.py#L91) |
| method | `GridBotV2.__init__` | `(self, api_key=…, api_secret=…, testnet=…, config=…)` | — | [src](../../../core/services/trading/grid_bot.py#L98) |
| method | `GridBotV2.get_price` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L132) |
| method | `GridBotV2.get_precision` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L138) |
| method | `GridBotV2.calculate_grid_levels` | `(self, center_price)` | — | [src](../../../core/services/trading/grid_bot.py#L149) |
| method | `GridBotV2.should_re_center` | `(self, current_price)` | — | [src](../../../core/services/trading/grid_bot.py#L167) |
| method | `GridBotV2.re_center_grid` | `(self, current_price)` | — | [src](../../../core/services/trading/grid_bot.py#L173) |
| method | `GridBotV2.check_stop_loss` | `(self, current_price)` | — | [src](../../../core/services/trading/grid_bot.py#L188) |
| method | `GridBotV2.update_drawdown` | `(self, current_value)` | — | [src](../../../core/services/trading/grid_bot.py#L197) |
| method | `GridBotV2.apply_autocompound` | `(self, pnl_from_cycle)` | — | [src](../../../core/services/trading/grid_bot.py#L208) |
| method | `GridBotV2.write_trading_state` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L218) |
| method | `GridBotV2.place_grid_orders` | `(self, levels)` | — | [src](../../../core/services/trading/grid_bot.py#L232) |
| method | `GridBotV2.cancel_all_orders` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L235) |
| method | `GridBotV2.stop` | `(self)` | — | [src](../../../core/services/trading/grid_bot.py#L238) |
| method | `GridBotV2.run_simulation` | `(self)` | Kør én cycle i simulation. Returnér liste af actions. | [src](../../../core/services/trading/grid_bot.py#L247) |
| method | `GridBotV2.run_once` | `(self)` | Alias for run_simulation — bruges af loop. | [src](../../../core/services/trading/grid_bot.py#L326) |
| function | `demo` | `()` | Demo-kørsel på Binance testnet — 3 cycles. | [src](../../../core/services/trading/grid_bot.py#L352) |
| function | `run_continuous` | `()` | Kør grid-bot i loop hvert 60. sekund indtil stoppet. | [src](../../../core/services/trading/grid_bot.py#L406) |

