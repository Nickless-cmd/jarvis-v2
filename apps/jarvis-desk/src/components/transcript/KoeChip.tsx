import type { KoetBesked } from '../../hooks/useSendeKoe'

/**
 * Den køede besked over skrivefeltet. Claude Desktops ord (§6): «1 message
 * queued. Will send after the current response.» ×-knappen fjerner den fra
 * køen — den afbryder ALDRIG turen der kører.
 */
export function KoeChip({ koet, online, onAnnuller }: { koet: KoetBesked | null; online: boolean; onAnnuller: () => void }) {
  if (!koet) return null
  return (
    <div className={`queued-chip ${!online ? 'is-offline' : ''}`} data-testid="koe-chip">
      <span className="queued-label">{!online ? 'Offline — sendes når forbindelsen er tilbage' : 'I kø — sendes efter svaret'}</span>
      <span className="queued-text">{koet.text}</span>
      <button type="button" className="queued-cancel" onClick={onAnnuller} aria-label="Fjern fra kø">×</button>
    </div>
  )
}
