import { safeImageSrc } from '../../lib/sanitize'
import { KlikbartBillede } from './BilledLightbox'

/** Billede-output (Jarvis' vision/ComfyUI). Kilde valideres: tilladt er
 *  backend-attachments (/...) + https:. file:/data:/svg-uri blokeres → vis
 *  alt-tekst placeholder i stedet.
 *
 *  Kilden er en data-URL direkte fra streamen — derfor kan den gå direkte i
 *  `<img>`, i modsætning til det gemte billede (se AttachmentBlock, der henter
 *  med token). Klik åbner fuld størrelse (Bjørn 20/9-2026). */
export function ImageBlock({ src, alt }: { src: string; alt?: string }) {
  const safe = safeImageSrc(src)
  if (!safe) return <span className="image-blocked">{alt || 'billede blokeret'}</span>
  return <KlikbartBillede src={safe} alt={alt} />
}
