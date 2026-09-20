import { useEffect, useState } from 'react'
import { AlertCircle, FileText, Loader2 } from 'lucide-react'
import { useSettings } from '../../hooks/useSettings'
import { downloadBlob, fetchBlobWithAuth, type ApiConfig } from '../../lib/api'
import { KlikbartBillede } from './BilledLightbox'

/**
 * En fil Jarvis har lagt ud — eller et gemt billede.
 *
 * ## Hvorfor den findes
 *
 * Blokken bærer kun en REFERENCE. Både `/files/{navn}` og `/attachments/...`
 * kræver godkendelse (målt 12/9-2026: 401 uden `Authorization`), så et
 * almindeligt link eller et `<img src>` ville give «unauthorized» på en fil der
 * findes og er ens egen. Vi henter den derfor selv med token og gemmer den
 * under dens rigtige navn.
 *
 * ## De to slags referencer
 *
 *   - `url`          — en fil Jarvis selv udgav med `publish_file` (`/files/…`)
 *   - `attachment_id` — en upload eller et genereret billede (`/attachments/…`)
 *
 * En udgivet fil har ALDRIG et attachment_id. Det er præcis derfor
 * `foldToolResults` tidligere droppede den: typen fandtes ikke i kæden, og
 * filen nåede aldrig skærmen (målt 15/9-2026 på et regneark der skulle leveres
 * i chatten). Spejler mobilens `MessageAttachments` — samme kontrakt.
 */

/** Den slags blokke denne komponent kan vise. */
export interface VedhaefningsBlok {
  type: 'image' | 'file'
  filename?: string
  url?: string
  attachment_id?: string
  mime_type?: string
  size_bytes?: number
}

/** Hvilken adresse hører blokken til? Spejler mobilens `blokUrl`. */
export function filAdresse(block: VedhaefningsBlok): string {
  const direkte = String(block.url || '').trim()
  if (direkte) return direkte
  const id = String(block.attachment_id || '').trim()
  if (!id) return ''
  return block.type === 'image'
    ? `/attachments/image/${encodeURIComponent(id)}`
    : `/attachments/${encodeURIComponent(id)}`
}

/** 1536 → «1,5 kB». Dansk komma — samme regel som mobilen. */
export function formatSize(bytes?: number): string {
  if (typeof bytes !== 'number' || !(bytes > 0)) return ''
  if (bytes < 1024) return `${bytes} B`
  const units = ['kB', 'MB', 'GB']
  let value = bytes / 1024
  let i = 0
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024
    i++
  }
  const rounded = Math.round(value * 10) / 10
  const text = Number.isInteger(rounded) ? String(rounded) : String(rounded).replace('.', ',')
  return `${text} ${units[i]}`
}

export function AttachmentBlock({ block }: { block: VedhaefningsBlok }) {
  const { settings } = useSettings()
  const config: ApiConfig | null = settings
    ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    : null

  const adresse = filAdresse(block)
  const navn = String(block.filename || (block.type === 'image' ? 'billede' : 'fil'))

  // Billeder: hentes til en object-URL og vises som flade. Filer: hentes ved
  // klik og gemmes. To spor, fordi man SER et billede og GEMMER en fil.
  const [billedeUrl, setBilledeUrl] = useState<string | null>(null)
  const [henter, setHenter] = useState(false)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (block.type !== 'image' || !config || !adresse) return
    let afbrudt = false
    let lavet: string | null = null
    setHenter(true)
    setFejl(false)
    fetchBlobWithAuth(config, adresse)
      .then((blob) => {
        if (afbrudt) return
        lavet = URL.createObjectURL(blob)
        setBilledeUrl(lavet)
      })
      .catch(() => { if (!afbrudt) setFejl(true) })
      .finally(() => { if (!afbrudt) setHenter(false) })
    return () => {
      afbrudt = true
      if (lavet) URL.revokeObjectURL(lavet)
    }
    // `adresse` og `config` er de eneste indgange der ændrer hvad der hentes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adresse, block.type, settings])

  if (block.type === 'image') {
    if (fejl) return <span className="attachment-fejl"><AlertCircle size={14} /> {navn} kunne ikke hentes</span>
    if (!billedeUrl) return <span className="attachment-fejl">{henter ? <Loader2 size={14} className="spin" /> : null} {navn}</span>
    // Klik åbner fuld størrelse (Bjørn 20/9-2026). Formen kommer fra
    // `.attachment-image` — men uden `object-fit: cover`, som KLIPPEDE
    // kanterne af ens eget billede.
    return <KlikbartBillede className="attachment-image" src={billedeUrl} alt={navn} />
  }

  const stoerrelse = formatSize(block.size_bytes)

  const hent = () => {
    if (!config || !adresse || henter) return
    setHenter(true)
    setFejl(false)
    fetchBlobWithAuth(config, adresse)
      .then((blob) => downloadBlob(blob, navn))
      .catch(() => setFejl(true))
      .finally(() => setHenter(false))
  }

  return (
    <button
      type="button"
      className="file-block"
      onClick={hent}
      disabled={!config || !adresse || henter}
      title={adresse ? `Hent ${navn}` : 'Filen har ingen adresse'}
    >
      {henter ? <Loader2 size={15} className="spin" /> : fejl ? <AlertCircle size={15} /> : <FileText size={15} />}
      <span className="file-block-name">{navn}</span>
      {stoerrelse ? <span className="file-block-size">{stoerrelse}</span> : null}
      {fejl ? <span className="file-block-size">kunne ikke hentes</span> : null}
    </button>
  )
}
