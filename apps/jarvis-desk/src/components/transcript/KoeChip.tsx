import { useState } from 'react'
import { ArrowDown, ArrowUp, Check, Pencil, Send, X } from 'lucide-react'
import type { KoetItem } from '../../hooks/useSendeKoe'

/**
 * De køede beskeder over skrivefeltet. Claude Desktops ord (§6): «1 message
 * queued. Will send after the current response.»
 *
 * 3/10-2026 (Bjørn): «que beskeder over composer mangler styr funktion lige
 * som i mobilen … så det findes allerede». Før havde chippen kun en ×-knap.
 * Nu har hver besked samme styring som mobilens `KoeChip`: rediger, flyt
 * op/ned, «send nu» (midt i et kørende run via serverens steer) og fjern.
 * Ingen af dem afbryder turen der kører.
 */
export function KoeChip({ items, busy, kanSteer, error, online, onRediger, onFjern, onFlyt, onSendNu }: {
  items: KoetItem[]
  busy: boolean
  kanSteer: boolean
  error?: string
  online: boolean
  onRediger: (id: number, text: string) => void
  onFjern: (id: number) => void
  onFlyt: (id: number, retning: -1 | 1) => void
  onSendNu: (id: number) => void
}) {
  const [redigerId, setRedigerId] = useState<number | null>(null)
  const [kladde, setKladde] = useState('')
  if (!items.length && !error) return null
  return (
    <div className={`queued-chip${!online ? ' is-offline' : ''}`} data-testid="koe-chip">
      <span className="queued-label">
        {!online
          ? 'Offline — sendes når forbindelsen er tilbage'
          : `I kø — sendes efter svaret${items.length > 1 ? ` (${items.length})` : ''}`}
      </span>
      <ul className="queued-liste">
        {items.map((item, i) => (
          <li key={item.id} className="queued-item" data-testid={`koe-item-${item.id}`}>
            {redigerId === item.id ? (
              <input
                className="queued-input"
                value={kladde}
                autoFocus
                aria-label="Rediger køet besked"
                onChange={(e) => setKladde(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { onRediger(item.id, kladde.trim()); setRedigerId(null) }
                  if (e.key === 'Escape') setRedigerId(null)
                }}
              />
            ) : (
              <span className="queued-text" title={item.text}>{item.text}</span>
            )}
            <span className="queued-actions">
              {redigerId === item.id ? (
                <>
                  <button type="button" aria-label="Gem ændring" disabled={!kladde.trim()}
                    onClick={() => { onRediger(item.id, kladde.trim()); setRedigerId(null) }}><Check size={15} /></button>
                  <button type="button" aria-label="Fortryd redigering" onClick={() => setRedigerId(null)}><X size={15} /></button>
                </>
              ) : (
                <>
                  <button type="button" aria-label="Rediger køet besked"
                    onClick={() => { setRedigerId(item.id); setKladde(item.text) }}><Pencil size={14} /></button>
                  <button type="button" aria-label="Flyt op" disabled={i === 0}
                    onClick={() => onFlyt(item.id, -1)}><ArrowUp size={14} /></button>
                  <button type="button" aria-label="Flyt ned" disabled={i === items.length - 1}
                    onClick={() => onFlyt(item.id, 1)}><ArrowDown size={14} /></button>
                  <button type="button" aria-label={busy ? 'Send nu til det kørende run' : 'Send nu'}
                    disabled={busy && !kanSteer} onClick={() => onSendNu(item.id)}><Send size={14} /></button>
                  <button type="button" aria-label="Fjern fra kø"
                    onClick={() => onFjern(item.id)}><X size={15} /></button>
                </>
              )}
            </span>
          </li>
        ))}
      </ul>
      {error ? <p className="queued-fejl" role="alert">{error}</p> : null}
    </div>
  )
}
