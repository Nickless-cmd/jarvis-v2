interface TokenInfo {
  total_tokens?: number
  input_tokens?: number
  output_tokens?: number
}

interface Props {
  apiBaseUrl: string
  mode: 'dev' | 'thin-client' | 'standalone'
  backendUp: boolean
  latencyMs?: number
  lastRunTokens?: TokenInfo | null
  streamingTokenEstimate?: number | null
  // Compact threshold from runtime config — the soft cap before /compact
  // is recommended. Hardcoded default matches runtime.json's 40k.
  compactThreshold?: number
}

export function StatusBar({
  apiBaseUrl,
  mode,
  backendUp,
  latencyMs,
  lastRunTokens,
  streamingTokenEstimate,
  compactThreshold = 40000,
}: Props) {
  // Effective tokens used in last visible run, or the live streaming
  // estimate if a run is in progress. Falls back to the larger of the
  // two so the gauge doesn't snap backward mid-stream.
  const effective =
    streamingTokenEstimate && streamingTokenEstimate > (lastRunTokens?.total_tokens || 0)
      ? streamingTokenEstimate
      : lastRunTokens?.total_tokens || 0
  const pct = compactThreshold > 0 ? effective / compactThreshold : 0
  const tone =
    pct >= 0.95 ? 'critical' : pct >= 0.75 ? 'warn' : pct >= 0.5 ? 'mid' : 'ok'
  const toneColor = {
    ok: '#3fb950',
    mid: '#5ab8a0',
    warn: '#d4963a',
    critical: '#f85149',
  }[tone]

  return (
    <footer className="flex items-center gap-4 border-t border-line bg-bg1 px-4 py-1.5 text-[10px] text-fg3">
      <div className="flex items-center gap-1.5">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            backendUp ? 'bg-ok shadow-[0_0_6px_rgba(63,185,80,0.6)]' : 'bg-danger'
          }`}
        />
        <span className="font-mono">
          {backendUp
            ? `runtime up${latencyMs != null ? ` · ${latencyMs}ms` : ''}`
            : 'runtime down'}
        </span>
      </div>
      <span className="font-mono">{mode}</span>
      {/* Token budget gauge — last run's total / compact threshold.
          Color escalates green → teal → amber → red as we approach
          the soft cap. Helps Jarvis (and Bjørn) see when context is
          getting thick before /compact silently strips it. */}
      {effective > 0 && (
        <div
          className="flex items-center gap-1.5"
          title={`Tokens i seneste run: ${effective.toLocaleString()} / ${compactThreshold.toLocaleString()} compact-threshold`}
        >
          <div
            className="relative h-1.5 w-20 overflow-hidden rounded-full"
            style={{ background: '#21262d' }}
          >
            <div
              className="h-full transition-all duration-500 ease-out"
              style={{
                width: `${Math.min(100, pct * 100)}%`,
                background: `linear-gradient(90deg, ${toneColor}80, ${toneColor})`,
              }}
            />
          </div>
          <span className="font-mono tabular-nums" style={{ color: toneColor }}>
            {formatTokens(effective)} / {formatTokens(compactThreshold)}
          </span>
        </div>
      )}
      <span className="font-mono opacity-60">{apiBaseUrl}</span>
      <span className="ml-auto opacity-50">JarvisX 0.1.0-poc</span>
    </footer>
  )
}

function formatTokens(n: number): string {
  if (n < 1000) return String(n)
  if (n < 1_000_000) return `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`
  return `${(n / 1_000_000).toFixed(1)}M`
}
