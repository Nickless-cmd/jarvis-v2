import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getConnectors, startConnect, type Connector } from '../../lib/connectorsApi'
import { connectorIcon } from '../../lib/connectorIcon'
import { greetingFor } from '../../lib/greeting'
import { takePendingHint } from '../../lib/postConnect'

function openBrowser(url: string): void {
  const b = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => Promise<void> } }).jarvisDesk
  void b?.openExternal?.(url)
}

/** Tom-session-skærm: tids-bevidst greeting + presence-ring tonet efter tidspunkt
 *  + op til 3 connector-forslag (kun ikke-forbundne) + "Flere apps →". Composeren
 *  gives som children, så den sidder under hilsenen (spec §3.4). */
export function GreetingHero({
  config, userName, onOpenMarketplace, onSuggest, children,
}: {
  config?: ApiConfig
  userName: string
  onOpenMarketplace: () => void
  onSuggest?: (text: string) => void
  children: ReactNode
}) {
  // Random men stabil pr. mount (seed varierer mellem sessioner — "random greeting").
  const g = useMemo(() => greetingFor(new Date(), Math.floor(Math.random() * 1000)), [])
  const [suggestions, setSuggestions] = useState<Connector[]>([])
  // Post-connect-hook (engangs): lige forbundet → tilbyd connector-specifikt forslag.
  const [hint, setHint] = useState<string | null>(null)
  useEffect(() => { setHint(takePendingHint()) }, [])

  useEffect(() => {
    if (!config) return
    let cancelled = false
    void getConnectors(config)
      .then((list) => {
        if (cancelled) return
        // Vis OAuth-apps (både forbundne m. ✓ og ikke-forbundne) — Gmail først,
        // forbundne sidst. Maks 4 (som Codex).
        const oauth = list.filter((c) => c.kind === 'oauth' && c.status !== 'coming_soon')
        oauth.sort((a, b) => {
          if (a.id === 'gmail') return -1
          if (b.id === 'gmail') return 1
          return Number(a.connected) - Number(b.connected)
        })
        setSuggestions(oauth.slice(0, 4))
      })
      .catch(() => { /* tom — ingen forslag er fint */ })
    return () => { cancelled = true }
  }, [config])

  const onConnect = async (c: Connector) => {
    if (!config || c.connected) return
    const url = await startConnect(config, c.id).catch(() => null)
    if (url) openBrowser(url)
  }

  return (
    <div className="greeting-hero">
      <div className="greeting-top">
        <div className="greeting-ring" style={{ ['--tint' as string]: g.tint }}>{g.glyph}</div>
        <div className="greeting-hello">{g.hello}, {userName} {g.glyph}</div>
        <div className="greeting-line">{g.line}</div>
      </div>

      {hint && (
        <div className="greeting-hint">
          <span className="greeting-hint-text">{hint}</span>
          <button type="button" className="greeting-hint-yes" onClick={() => { onSuggest?.(hint); setHint(null) }}>Ja tak</button>
          <button type="button" className="greeting-hint-no" aria-label="Afvis" onClick={() => setHint(null)}>×</button>
        </div>
      )}

      {children}

      <div className="greeting-connectors">
        {suggestions.length > 0 && (
          <>
            <div className="greeting-connectors-label">Forbind dine apps</div>
            <div className="greeting-connectors-row">
              {suggestions.map((c) => {
                const Icon = connectorIcon(c.icon)
                return (
                  <button
                    key={c.id}
                    type="button"
                    className={`greeting-connector ${c.connected ? 'is-connected' : ''}`}
                    onClick={() => onConnect(c)}
                    disabled={c.connected}
                  >
                    <span className="greeting-connector-icon"><Icon size={16} /></span>
                    <span className="greeting-connector-body">
                      <span className="greeting-connector-name">{c.name}</span>
                      <span className="greeting-connector-desc">{c.desc}</span>
                    </span>
                    <span className="greeting-connector-cta">
                      {c.connected ? '✓ Forbundet' : 'Forbind'}
                    </span>
                  </button>
                )
              })}
            </div>
          </>
        )}
        <div className="greeting-more">
          <button type="button" onClick={onOpenMarketplace}>Flere apps →</button>
        </div>
      </div>
    </div>
  )
}
