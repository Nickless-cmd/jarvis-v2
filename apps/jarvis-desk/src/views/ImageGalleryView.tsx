import { useEffect, useState } from 'react'
import { useSettings } from '../hooks/useSettings'
import { useSessions } from '../hooks/useSessions'
import { listImages, fetchImageObjectUrl, type ImageAttachment, type ApiConfig } from '../lib/api'
import { ListeTilstand } from '../components/feedback/ListeTilstand'

/** Galleri (#6): billeder du og Jarvis har uploadet, på tværs af samtaler.
 *  Klik et billede → hop til den samtale det hører til. */
export function ImageGalleryView({ onOpenChat }: { onOpenChat: () => void }) {
  const { settings } = useSettings()
  const { select } = useSessions()
  const [images, setImages] = useState<ImageAttachment[]>([])
  const [loading, setLoading] = useState(true)
  // `catch → setImages([])` sagde «ingen billeder uploadet endnu» når
  // hentningen slog fejl. Man kan ikke kende forskel, og så leder man efter
  // billeder man selv har uploadet.
  const [fejl, setFejl] = useState(false)
  const [igen, setIgen] = useState(0)

  const config: ApiConfig | null = settings
    ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    : null

  useEffect(() => {
    if (!config) return
    let cancelled = false
    setLoading(true)
    listImages(config)
      .then((r) => { if (!cancelled) { setImages(r); setFejl(false) } })
      .catch(() => { if (!cancelled) setFejl(true) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings, igen])

  const openSession = (sessionId: string) => { select(sessionId); onOpenChat() }

  return (
    <div className="gallery">
      <div className="gallery-head"><h2>Billeder</h2></div>
      {loading || fejl || images.length === 0 ? (
        <ListeTilstand
          henter={loading} fejl={fejl} navn="billederne"
          antal={images.length} tomTekst="Ingen billeder uploadet endnu."
          onIgen={fejl ? () => { setLoading(true); setIgen((n) => n + 1) } : null}
        />
      ) : (
        <div className="gallery-grid">
          {config && images.map((img) => (
            <GalleryThumb
              key={img.attachment_id}
              config={config}
              image={img}
              onOpen={() => openSession(img.session_id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function GalleryThumb({
  config,
  image,
  onOpen,
}: {
  config: ApiConfig
  image: ImageAttachment
  onOpen: () => void
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let url: string | null = null
    let cancelled = false
    fetchImageObjectUrl(config, image.attachment_id)
      .then((u) => { if (cancelled) { URL.revokeObjectURL(u) } else { url = u; setSrc(u) } })
      .catch(() => { if (!cancelled) setFailed(true) })
    return () => { cancelled = true; if (url) URL.revokeObjectURL(url) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image.attachment_id])

  return (
    <button type="button" className="gallery-thumb" onClick={onOpen} title={`${image.filename} — åbn samtale`}>
      {failed ? (
        <span className="gallery-thumb-fail">⚠</span>
      ) : src ? (
        <img src={src} alt={image.filename} loading="lazy" />
      ) : (
        <span className="gallery-thumb-loading" />
      )}
      <span className="gallery-thumb-name">{image.filename}</span>
    </button>
  )
}
