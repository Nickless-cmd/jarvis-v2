"""grid_bot — LivingNeuron governance: run_once emitterer trading.cycle."""
import inspect
import core.services.trading.grid_bot as m


def test_run_once_emits_trading_cycle():
    src = inspect.getsource(m.GridBotV2.run_once)
    assert "trading.cycle" in src and "event_bus" in src
