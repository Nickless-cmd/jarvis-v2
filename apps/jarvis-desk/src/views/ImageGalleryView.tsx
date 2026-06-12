import { useEffect, useState } from 'react'
import { useSettings } from '../hooks/useSettings'
import { useSessions } from '../hooks/useSessions'
import { listImages, fetchImageObjectUrl, type ImageAttachment, type ApiConfig } from '../lib/api'

/** Galleri (#6): billeder du og Jarvis har uploadet, på tværs af samtaler.
 *  Klik et billede → hop til den samtale det hører til. */
export function ImageGalleryView({ onOpenChat }: { onOpenChat: () => void }) {
  const { settings } = useSettings()
  const { select } = useSessions()
  const [images, setImages] = useState<ImageAttachment[]>([])
  const [loading, setLoading] = useState(true)

  const config: ApiConfig | null = settings
    ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    : null

  useEffect(() => {
    if (!config) return
    let cancelled = false
    setLoading(true)
    listImages(config)
      .then((r) => { if (!cancelled) setImages(r) })
      .catch(() => { if (!cancelled) setImages([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings])

  const openSession = (sessionId: string) => { select(sessionId); onOpenChat() }

  return (
    <div className="gallery">
      <div className="gallery-head"><h2>Billeder</h2></div>
      {loading ? (
        <p className="gallery-empty">Henter…</p>
      ) : images.length === 0 ? (
        <p className="gallery-empty">Ingen billeder uploadet endnu.</p>
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
