import { useEffect, useMemo, useState, type ReactNode } from 'react'
import type { ApiConfig } from '../../lib/api'
import { getConnectors, startConnect, type Connector } from '../../lib/connectorsApi'
import { connectorIcon } from '../../lib/connectorIcon'
import { greetingFor } from '../../lib/greeting'
import { takePendingHint } from '../../lib/postConnect'
import { prepareExternalWindow } from '../../lib/host'

/** Returnerer null naar der slet ingen bro er (web-fanen) — ellers selve
 *  loeftet, saa kalderen kan se om browseren faktisk aabnede. */
/** Tom-session-skærm: tids-bevidst greeting + op til 3 connector-forslag (kun
 *  ikke-forbundne). Composeren gives som children, så den sidder under hilsenen. */
/** Chat: hukommelse og samtale — det fladen ER til. */
const CHAT_FORSLAG = [
  'Hvad talte vi om sidst?',
  'Hvad ved du om mig?',
  'Hvad har du lavet i dag?',
]

/** Code: de vaerktoejer der faktisk findes i code-scope. */
const KODE_FORSLAG = [
  'Brug explore til at finde hvor X håndteres',
  'Hvad står der i git-status lige nu?',
  'Hvad kan jeg fortryde? (checkpoint)',
]

export function GreetingHero({
  config, userName, onSuggest, mode = 'chat', children,
}: {
  config?: ApiConfig
  userName: string
  onSuggest?: (text: string) => void
  /** Hvilken flade man staar paa — afgoer hvilke forslag der giver mening. */
  mode?: 'chat' | 'code'
  children: ReactNode
}) {
  // Random men stabil pr. mount (seed varierer mellem sessioner — "random greeting").
  const g = useMemo(() => greetingFor(new Date(), Math.floor(Math.random() * 1000)), [])
  const [suggestions, setSuggestions] = useState<Connector[]>([])
  // Post-connect-hook (engangs): lige forbundet → tilbyd connector-specifikt forslag.
  const [hint, setHint] = useState<string | null>(null)
  const [forbindFejl, setForbindFejl] = useState('')
  useEffect(() => { setHint(takePendingHint()) }, [])

  useEffect(() => {
    if (!config) return
    let cancelled = false
    void getConnectors(config)
      .then((list) => {
        if (cancelled) return
        // Opsætningen er en engangshandling: vis kun ikke-forbundne OAuth-apps,
        // Gmail først og højst tre diskrete forslag.
        const oauth = list.filter(
          (c) => c.kind === 'oauth' && c.status !== 'coming_soon' && !c.connected,
        )
        oauth.sort((a, b) => {
          if (a.id === 'gmail') return -1
          if (b.id === 'gmail') return 1
          return 0
        })
        setSuggestions(oauth.slice(0, 3))
      })
      .catch(() => { /* tom — ingen forslag er fint */ })
    return () => { cancelled = true }
  }, [config])

  // Codex' punkt 2 (21/9-2026): «Forbind» kunne fejle HELT tavst. Tre steder
  // kunne det gaa galt — ingen url, ingen bro, en browser der ikke aabnede —
  // og alle tre saa ens ud: intet skete. Det er den vaerste slags knap.
  const onConnect = async (c: Connector) => {
    if (!config || c.connected) return
    setForbindFejl('')
    const completeWindow = prepareExternalWindow()
    const url = await startConnect(config, c.id).catch(() => null)
    if (!url) {
      completeWindow(null)
      setForbindFejl(`${c.name} kunne ikke forberedes. Proev igen, eller gaa ind under Flere apps.`)
      return
    }
    if (!completeWindow(url)) {
      setForbindFejl(`Browseren åbnede ikke med ${c.name}. Tillad popups og prøv igen.`)
      return
    }
  }

  return (
    <div className="greeting-hero">
      <div className="greeting-top">
        <div className="greeting-hello">{g.hello}, {userName}</div>
        <div className="greeting-line">{g.line}</div>
      </div>

      {hint && (
        <div className="greeting-hint">
          <span className="greeting-hint-text">{hint}</span>
          <button type="button" className="greeting-hint-yes" onClick={() => { onSuggest?.(hint); setHint(null) }}>Ja tak</button>
          <button type="button" className="greeting-hint-no" aria-label="Afvis" onClick={() => setHint(null)}>×</button>
        </div>
      )}

      {/* Mode-afhaengige startforslag (6/9-2026, Codex' punkt 9).
          Forslagene er ting Jarvis FAKTISK kan paa den flade — ikke
          inspiration. Et forslag der fejler naar man trykker paa det er
          vaerre end ingen forslag. */}
      {onSuggest && (
        <div className="greeting-starters">
          {(mode === 'code' ? KODE_FORSLAG : CHAT_FORSLAG).map((f) => (
            <button key={f} type="button" className="greeting-starter"
                    onClick={() => onSuggest(f)}>
              {f}
            </button>
          ))}
        </div>
      )}

      {children}

      <div className="greeting-connectors">
        {suggestions.length > 0 && (
          <div className="greeting-connectors-row">
            {suggestions.map((c) => {
              const Icon = connectorIcon(c.icon)
              return (
                <button
                  key={c.id}
                  type="button"
                  className="greeting-connector"
                  title={`Forbind ${c.name}`}
                  onClick={() => onConnect(c)}
                >
                  <span className="greeting-connector-icon"><Icon size={14} /></span>
                  <span className="greeting-connector-name">{c.name}</span>
                </button>
              )
            })}
          </div>
        )}
        {forbindFejl && (
          <p className="greeting-forbind-fejl" role="alert">{forbindFejl}</p>
        )}
      </div>
    </div>
  )
}
