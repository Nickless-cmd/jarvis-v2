import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Pause,
  Play,
  CircleDot,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  Wallet,
  Activity,
  Loader2,
} from 'lucide-react'

interface TradingConfig {
  grid_levels?: number
  grid_spacing_pct?: number
  order_size_usdt?: number
  stop_loss_pct?: number
}

interface Capital {
  usdt: number
  asset: number
  asset_symbol: string
  total_value_usdt: number
  starting_value_usdt: number
}

interface Pnl {
  realized_today: number
  realized_total: number
  unrealized: number
  fees_today: number
  fees_total: number
}

interface Drawdown {
  current_pct: number
  max_pct_today: number
  cap_pct: number
}

interface OpenOrder {
  id: string
  side: 'BUY' | 'SELL'
  price: number
  quantity: number
  placed_at: string
}

interface Trade {
  type: 'BUY' | 'SELL'
  price: number
  qty: number
  profit_usdt?: number
  timestamp: string
}

interface TradingState {
  status: 'inactive' | 'active' | 'paused' | 'stopped' | 'error' | string
  mode: 'paper' | 'simulation' | 'testnet' | 'live' | string
  symbol: string
  config: TradingConfig
  capital: Capital
  pnl: Pnl
  drawdown: Drawdown
  trades_today: number
  open_orders: OpenOrder[]
  recent_trades: Trade[]
  last_price: number
  last_updated: string | null
  last_error?: string
  _inactive_reason?: string
  _state_file_mtime?: number
}

interface Props {
  apiBaseUrl: string
}

const POLL_MS = 4000

/**
 * Read-only trading dashboard for Jarvis' grid bot.
 *
 * The bot's state lives in ~/.jarvis-v2/state/trading_state.json
 * (Jarvis writes; this view reads). Nothing in this component
 * mutates trading state — that's deliberate. Trading actions go
 * through the bot's own lifecycle, not the dashboard.
 *
 * Layout:
 *   - Status header: status pill (active/paused/stopped/error),
 *     mode badge (paper/sim/testnet/live), symbol, last updated
 *   - Top stats: total value, USDT/asset balance, realized PnL today
 *   - Drawdown bar: current vs cap, with warning shading at 80%
 *   - Fee burn: today/total + % of theoretical profit
 *   - Open orders table
 *   - Recent trades table (capped at 20)
 */
export function TradingView({ apiBaseUrl }: Props) {
  const [state, setState] = useState<TradingState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch(`${baseUrl}/api/trading/state`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as TradingState
      setState(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [baseUrl])

  useEffect(() => {
    void refresh()
    const id = window.setInterval(refresh, POLL_MS)
    return () => window.clearInterval(id)
  }, [refresh])

  const inactive = !state || state.status === 'inactive'
  const stale = useMemo(() => {
    if (!state?._state_file_mtime) return false
    const ageSec = Date.now() / 1000 - state._state_file_mtime
    return ageSec > 60
  }, [state])

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-bg0">
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <Activity size={14} className="text-accent" />
          <h2 className="text-sm font-semibold">Trading</h2>
          {state && state.symbol && (
            <span className="font-mono text-[11px] text-fg2">{state.symbol}</span>
          )}
          {state && <StatusPill status={state.status} mode={state.mode} />}
          {stale && (
            <span
              className="flex items-center gap-1 rounded bg-warn/15 px-1.5 py-0.5 text-[10px] text-warn"
              title="State file hasn't been updated in over 60s"
            >
              <CircleDot size={9} />
              stale
            </span>
          )}
        </div>
        <button
          onClick={() => void refresh()}
          title="Genindlæs"
          disabled={loading}
          className="flex h-7 w-7 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg disabled:opacity-50"
        >
          {loading ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
        </button>
      </header>

      {error && (
        <div className="flex flex-shrink-0 items-start gap-2 border-b border-danger/30 bg-danger/10 px-4 py-2">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[11px] text-danger">{error}</span>
        </div>
      )}

      {state?.last_error && (
        <div className="flex flex-shrink-0 items-start gap-2 border-b border-danger/30 bg-danger/10 px-4 py-2">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[11px] text-danger">
            Bot error: {state.last_error}
          </span>
        </div>
      )}

      {inactive ? (
        <InactivePane reason={state?._inactive_reason} />
      ) : state ? (
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-6 py-5">
          <StatsRow state={state} />
          <DrawdownBar drawdown={state.drawdown} />
          <FeeBurnPanel pnl={state.pnl} config={state.config} />
          <OpenOrdersTable orders={state.open_orders} symbol={state.symbol} />
          <RecentTradesTable trades={state.recent_trades} />
          <FooterMeta state={state} />
        </div>
      ) : null}
    </div>
  )
}

function InactivePane({ reason }: { reason?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center text-center">
      <div className="max-w-[420px] px-6">
        <Activity size={32} className="mx-auto mb-3 opacity-30" />
        <div className="mb-2 text-sm font-medium text-fg2">
          Trading-bot er inaktiv
        </div>
        <p className="text-[11px] leading-relaxed text-fg3">
          Jarvis skriver state til{' '}
          <code className="font-mono text-fg2">
            ~/.jarvis-v2/state/trading_state.json
          </code>{' '}
          når bot'en kører. Indtil da viser dette panel ingen tal —
          trading-handlinger kører ikke gennem dashboard'et, kun observation.
        </p>
        {reason && (
          <p className="mt-2 font-mono text-[10px] text-fg3/70">{reason}</p>
        )}
      </div>
    </div>
  )
}

function StatusPill({ status, mode }: { status: string; mode: string }) {
  const map: Record<string, { label: string; cls: string; Icon: typeof Activity }> = {
    active: { label: 'kører', cls: 'bg-ok/15 text-ok ring-ok/30', Icon: Play },
    paused: { label: 'pauset', cls: 'bg-warn/15 text-warn ring-warn/30', Icon: Pause },
    stopped: { label: 'stoppet', cls: 'bg-bg2 text-fg3 ring-line2', Icon: Pause },
    error: { label: 'fejl', cls: 'bg-danger/15 text-danger ring-danger/30', Icon: AlertTriangle },
    inactive: { label: 'inaktiv', cls: 'bg-bg2 text-fg3 ring-line2', Icon: CircleDot },
  }
  const meta = map[status] ?? map.inactive
  const modeCls =
    mode === 'live'
      ? 'bg-danger/15 text-danger ring-danger/30'
      : 'bg-bg2 text-fg3 ring-line2'
  return (
    <>
      <span
        className={[
          'flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ring-1',
          meta.cls,
        ].join(' ')}
      >
        <meta.Icon size={9} />
        {meta.label}
      </span>
      <span
        className={[
          'rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ring-1',
          modeCls,
        ].join(' ')}
        title={
          mode === 'live'
            ? 'LIVE — handler med rigtige penge'
            : `${mode} — ingen rigtige penge`
        }
      >
        {mode}
      </span>
    </>
  )
}

function StatsRow({ state }: { state: TradingState }) {
  const totalPnl = state.pnl.realized_total + state.pnl.unrealized
  const startVal = state.capital.starting_value_usdt || 0
  const totalReturn =
    startVal > 0 ? ((state.capital.total_value_usdt - startVal) / startVal) * 100 : 0
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      <Stat
        label="Total value"
        value={`$${state.capital.total_value_usdt.toFixed(2)}`}
        sub={`start: $${startVal.toFixed(2)} (${formatPct(totalReturn)})`}
        tone={totalReturn >= 0 ? 'ok' : 'danger'}
        Icon={Wallet}
      />
      <Stat
        label="USDT"
        value={`$${state.capital.usdt.toFixed(2)}`}
        sub={`${state.capital.asset_symbol}: ${state.capital.asset.toFixed(6)}`}
        Icon={Wallet}
      />
      <Stat
        label="PnL i dag"
        value={`${formatSigned(state.pnl.realized_today)} USDT`}
        sub={`urealiseret: ${formatSigned(state.pnl.unrealized)}`}
        tone={state.pnl.realized_today >= 0 ? 'ok' : 'danger'}
        Icon={state.pnl.realized_today >= 0 ? TrendingUp : TrendingDown}
      />
      <Stat
        label="Total PnL"
        value={`${formatSigned(totalPnl)} USDT`}
        sub={`${state.trades_today} trades i dag`}
        tone={totalPnl >= 0 ? 'ok' : 'danger'}
        Icon={Activity}
      />
    </div>
  )
}

function Stat({
  label,
  value,
  sub,
  tone = 'neutral',
  Icon,
}: {
  label: string
  value: string
  sub?: string
  tone?: 'ok' | 'danger' | 'neutral'
  Icon: typeof Activity
}) {
  const valueCls =
    tone === 'ok'
      ? 'text-ok'
      : tone === 'danger'
      ? 'text-danger'
      : 'text-fg'
  return (
    <div className="rounded-md border border-line bg-bg1 px-3 py-2.5">
      <div className="mb-1 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg3">
        <Icon size={10} /> {label}
      </div>
      <div className={`font-mono text-base ${valueCls}`}>{value}</div>
      {sub && <div className="mt-1 font-mono text-[10px] text-fg3">{sub}</div>}
    </div>
  )
}

function DrawdownBar({ drawdown }: { drawdown: Drawdown }) {
  const cap = drawdown.cap_pct || 5
  const pct = Math.min(100, Math.abs(drawdown.current_pct) / cap * 100)
  const close = pct >= 80
  const exceeded = Math.abs(drawdown.current_pct) >= cap
  return (
    <div className="rounded-md border border-line bg-bg1 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wider text-fg3">
          Drawdown
          {exceeded && (
            <span className="rounded bg-danger/15 px-1.5 py-0.5 text-[9px] text-danger">
              CAP HIT
            </span>
          )}
        </div>
        <div className="font-mono text-[11px]">
          <span className={exceeded ? 'text-danger' : close ? 'text-warn' : 'text-fg2'}>
            {formatPct(drawdown.current_pct)}
          </span>
          <span className="mx-1.5 text-fg3">/</span>
          <span className="text-fg3">cap {cap.toFixed(1)}%</span>
        </div>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-bg2">
        <div
          className={[
            'h-full transition-all',
            exceeded ? 'bg-danger' : close ? 'bg-warn' : 'bg-accent',
          ].join(' ')}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 font-mono text-[10px] text-fg3">
        max i dag: {formatPct(drawdown.max_pct_today)}
      </div>
    </div>
  )
}

function FeeBurnPanel({ pnl, config }: { pnl: Pnl; config: TradingConfig }) {
  // Theoretical profit per trade is grid_spacing_pct of order_size_usdt;
  // fees on a round-trip are 2 × 0.1% = 0.2% of order_size_usdt by default.
  // % of theoretical profit lost to fees = (0.2 / spacing) * 100.
  const spacing = config.grid_spacing_pct || 0
  const feeBurnRatio = spacing > 0 ? (0.2 / spacing) * 100 : null
  return (
    <div className="rounded-md border border-line bg-bg1 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-fg3">
          Fee burn
        </div>
        {feeBurnRatio !== null && (
          <span
            className={[
              'rounded px-1.5 py-0.5 text-[10px] font-mono',
              feeBurnRatio >= 25
                ? 'bg-danger/15 text-danger'
                : feeBurnRatio >= 15
                ? 'bg-warn/15 text-warn'
                : 'bg-bg2 text-fg3',
            ].join(' ')}
            title="Andel af teoretisk profit der spises af fees ved 0.1% per side"
          >
            ~{feeBurnRatio.toFixed(1)}% af teoretisk profit
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4 text-[11px]">
        <div>
          <div className="font-mono text-fg2">
            ${pnl.fees_today.toFixed(4)}
          </div>
          <div className="text-[10px] text-fg3">i dag</div>
        </div>
        <div>
          <div className="font-mono text-fg2">
            ${pnl.fees_total.toFixed(4)}
          </div>
          <div className="text-[10px] text-fg3">total</div>
        </div>
      </div>
    </div>
  )
}

function OpenOrdersTable({
  orders,
  symbol,
}: {
  orders: OpenOrder[]
  symbol: string
}) {
  return (
    <div className="rounded-md border border-line bg-bg1">
      <div className="border-b border-line/60 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-fg3">
        Åbne ordrer · {orders.length}
      </div>
      {orders.length === 0 ? (
        <div className="px-4 py-3 text-[11px] italic text-fg3">
          Ingen åbne ordrer
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead className="text-fg3">
              <tr className="border-b border-line/40">
                <th className="px-4 py-1.5 text-left font-medium">Side</th>
                <th className="px-4 py-1.5 text-right font-medium">Pris</th>
                <th className="px-4 py-1.5 text-right font-medium">Mængde</th>
                <th className="px-4 py-1.5 text-right font-medium">Værdi</th>
                <th className="px-4 py-1.5 text-right font-medium">Placeret</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-line/20 last:border-b-0">
                  <td className="px-4 py-1.5">
                    {o.side === 'BUY' ? (
                      <span className="flex items-center gap-1 text-ok">
                        <ArrowUpRight size={11} /> BUY
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-danger">
                        <ArrowDownRight size={11} /> SELL
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono">
                    ${o.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono">
                    {o.quantity.toFixed(6)} {symbol.replace('USDT', '')}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono text-fg2">
                    ${(o.price * o.quantity).toFixed(2)}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono text-[10px] text-fg3">
                    {timeSince(o.placed_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function RecentTradesTable({ trades }: { trades: Trade[] }) {
  const recent = trades.slice(-20).reverse()
  return (
    <div className="rounded-md border border-line bg-bg1">
      <div className="border-b border-line/60 px-4 py-2 text-[11px] font-semibold uppercase tracking-wider text-fg3">
        Seneste trades · {trades.length} total
      </div>
      {recent.length === 0 ? (
        <div className="px-4 py-3 text-[11px] italic text-fg3">
          Ingen trades endnu
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead className="text-fg3">
              <tr className="border-b border-line/40">
                <th className="px-4 py-1.5 text-left font-medium">Type</th>
                <th className="px-4 py-1.5 text-right font-medium">Pris</th>
                <th className="px-4 py-1.5 text-right font-medium">Mængde</th>
                <th className="px-4 py-1.5 text-right font-medium">Profit</th>
                <th className="px-4 py-1.5 text-right font-medium">Tid</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((t, i) => (
                <tr key={i} className="border-b border-line/20 last:border-b-0">
                  <td className="px-4 py-1.5">
                    {t.type === 'BUY' ? (
                      <span className="flex items-center gap-1 text-ok">
                        <ArrowUpRight size={11} /> BUY
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-danger">
                        <ArrowDownRight size={11} /> SELL
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono">
                    ${t.price.toFixed(2)}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono">
                    {t.qty.toFixed(6)}
                  </td>
                  <td
                    className={[
                      'px-4 py-1.5 text-right font-mono',
                      t.profit_usdt === undefined
                        ? 'text-fg3'
                        : t.profit_usdt >= 0
                        ? 'text-ok'
                        : 'text-danger',
                    ].join(' ')}
                  >
                    {t.profit_usdt === undefined
                      ? '—'
                      : formatSigned(t.profit_usdt)}
                  </td>
                  <td className="px-4 py-1.5 text-right font-mono text-[10px] text-fg3">
                    {timeSince(t.timestamp)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function FooterMeta({ state }: { state: TradingState }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line/40 pt-3 font-mono text-[10px] text-fg3">
      <span>last price: ${state.last_price.toFixed(2)}</span>
      <span>·</span>
      <span>
        grid: {state.config.grid_levels ?? '?'} niveauer @{' '}
        {state.config.grid_spacing_pct?.toFixed(2) ?? '?'}%
      </span>
      <span>·</span>
      <span>order size: ${state.config.order_size_usdt?.toFixed(2) ?? '?'}</span>
      <span>·</span>
      <span>stop-loss: {state.config.stop_loss_pct?.toFixed(1) ?? '?'}%</span>
      <span className="ml-auto">
        last update:{' '}
        {state.last_updated
          ? new Date(state.last_updated).toLocaleTimeString()
          : '—'}
      </span>
    </div>
  )
}

function formatSigned(n: number): string {
  const s = n >= 0 ? '+' : ''
  return `${s}${n.toFixed(4)}`
}

function formatPct(n: number): string {
  const s = n >= 0 ? '+' : ''
  return `${s}${n.toFixed(2)}%`
}

function timeSince(iso: string): string {
  if (!iso) return '?'
  try {
    const t = new Date(iso).getTime()
    const ageSec = Math.floor((Date.now() - t) / 1000)
    if (ageSec < 60) return `${ageSec}s`
    if (ageSec < 3600) return `${Math.floor(ageSec / 60)}m`
    if (ageSec < 86400) return `${Math.floor(ageSec / 3600)}t`
    return `${Math.floor(ageSec / 86400)}d`
  } catch {
    return '?'
  }
}
