import { useEffect, useState } from 'react'
import { AlertCircle, Loader2 } from 'lucide-react'
import { useSettings } from '../../hooks/useSettings'
import { fetchBlobWithAuth, type ApiConfig } from '../../lib/api'
import { filAdresse, formatSize } from './AttachmentBlock'

/**
 * En video Jarvis har lavet — noget man SER, ikke henter.
 *
 * ## Hvorfor den findes
 *
 * Indtil 28/9-2026 lavede `as_blocks` en `file` ud af enhver video, så en
 * genereret video blev et download-kort. Man kunne hente den og åbne den i et
 * andet program; man kunne ikke se den i tråden.
 *
 * ## De to kilder
 *
 * LIVE bærer blokken en `src` (data-URL fra streamen) og kan gå direkte i
 * elementet — som `ImageBlock`. PERSISTERET bærer den kun en reference, og
 * `/attachments/...` kræver godkendelse (401 uden `Authorization`, målt
 * 12/9-2026), så et rent `<video src>` ville give «unauthorized» på ens egen
 * fil. Vi henter den selv med token og spiller fra en object-URL — samme
 * kontrakt som `AttachmentBlock` bruger for gemte billeder.
 *
 * `preload="metadata"`: en video kan være mange megabyte, og en tråd kan bære
 * flere. Vi henter dem alligevel som blob for at kunne sætte token på, men
 * elementet skal ikke selv begynde at buffere mere end det har brug for.
 */
export interface VideoBlok {
  type: 'video'
  src?: string
  url?: string
  attachment_id?: string
  filename?: string
  mime_type?: string
  size_bytes?: number
}

export function VideoBlock({ block }: { block: VideoBlok }) {
  const { settings } = useSettings()
  const config: ApiConfig | null = settings
    ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    : null

  const live = String(block.src || '').trim()
  const adresse = live ? '' : filAdresse(block)
  const navn = String(block.filename || 'video')

  const [hentetUrl, setHentetUrl] = useState<string | null>(null)
  const [henter, setHenter] = useState(false)
  const [fejl, setFejl] = useState(false)

  useEffect(() => {
    if (live || !config || !adresse) return
    let afbrudt = false
    let lavet: string | null = null
    setHenter(true)
    setFejl(false)
    fetchBlobWithAuth(config, adresse)
      .then((blob) => {
        if (afbrudt) return
        lavet = URL.createObjectURL(blob)
        setHentetUrl(lavet)
      })
      .catch(() => { if (!afbrudt) setFejl(true) })
      .finally(() => { if (!afbrudt) setHenter(false) })
    return () => {
      afbrudt = true
      // Uden dette bliver hver video i tråden liggende i hukommelsen indtil
      // fanen lukkes — og en video fylder langt mere end et billede.
      if (lavet) URL.revokeObjectURL(lavet)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adresse, live, settings])

  const kilde = live || hentetUrl

  if (fejl) {
    return (
      <span className="attachment-fejl">
        <AlertCircle size={14} /> {navn} kunne ikke hentes
      </span>
    )
  }
  if (!kilde) {
    return (
      <span className="attachment-fejl">
        {henter ? <Loader2 size={14} className="spin" /> : null} {navn}
      </span>
    )
  }

  const stoerrelse = formatSize(block.size_bytes)
  return (
    <figure className="video-block">
      <video
        className="video-block-player"
        src={kilde}
        controls
        preload="metadata"
        playsInline
      />
      <figcaption className="video-block-navn">
        {navn}
        {stoerrelse ? <span className="file-block-size"> {stoerrelse}</span> : null}
      </figcaption>
    </figure>
  )
}
