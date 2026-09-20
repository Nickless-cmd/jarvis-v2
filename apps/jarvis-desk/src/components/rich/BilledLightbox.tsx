import { useCallback, useEffect, useState } from 'react'
import { X } from 'lucide-react'

/**
 * Et billede man kan trykke på.
 *
 * Bjørn 20/9-2026: «preview er meget stor. men for småt til jeg kan se det,
 * men kan ikke trykke på det for at forstår det». Tre steder viste billeder
 * med tre forskellige regler — Jarvis' live-billede havde ingen højde-grænse,
 * det gemte var klippet i 320×360 med `object-fit: cover` (som SKJULER
 * kanterne af ens eget billede), og brugerens egne uploads i 280×320. Ingen af
 * dem kunne åbnes.
 *
 * Nu: én fælles form (se `.jarvis-body img` i app.css), og et tryk åbner
 * billedet i fuld størrelse over resten. Escape eller klik udenfor lukker.
 *
 * `src` er bevidst bare en streng: de tre steder bærer hver sin slags kilde —
 * en data-URL fra streamen, en blob-URL (AttachmentBlock henter selv med token,
 * fordi /files og /attachments svarer 401 uden) eller en almindelig URL. En
 * lightbox der kun kunne én af dem ville holde op med at virke efter reload.
 */
export function KlikbartBillede({
  src,
  alt,
  className,
}: {
  src: string
  alt?: string
  /** Beholdes så hvert sted kan bære sin egen form (fx `.attachment-image`). */
  className?: string
}) {
  const [aaben, setAaben] = useState(false)
  const luk = useCallback(() => setAaben(false), [])

  // Escape lukker — samme mønster som FileContextMenu, så det føles som
  // resten af appen i stedet for et fremmed element.
  useEffect(() => {
    if (!aaben) return
    const paaTast = (e: KeyboardEvent) => {
      if (e.key === 'Escape') luk()
    }
    window.addEventListener('keydown', paaTast)
    return () => window.removeEventListener('keydown', paaTast)
  }, [aaben, luk])

  return (
    <>
      <button
        type="button"
        className="billed-knap"
        onClick={() => setAaben(true)}
        aria-label={alt ? `Åbn ${alt} i fuld størrelse` : 'Åbn billedet i fuld størrelse'}
        title="Åbn i fuld størrelse"
      >
        <img className={className} src={src} alt={alt ?? ''} loading="lazy" />
      </button>
      {aaben && (
        // Klik hvor som helst lukker — også på baggrunden. Selve billedet
        // stopper boblen, så et klik på det ikke lukker ved en fejl.
        <div
          className="billed-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={alt || 'Billede'}
          onClick={luk}
        >
          <button type="button" className="billed-luk" aria-label="Luk" onClick={luk}>
            <X size={18} />
          </button>
          <img src={src} alt={alt ?? ''} onClick={(e) => e.stopPropagation()} />
        </div>
      )}
    </>
  )
}
