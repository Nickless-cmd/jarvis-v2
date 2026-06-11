import { safeImageSrc } from '../../lib/sanitize'

/** Billede-output (Jarvis' vision/ComfyUI). Kilde valideres: tilladt er
 *  backend-attachments (/...) + https:. file:/data:/svg-uri blokeres → vis
 *  alt-tekst placeholder i stedet. */
export function ImageBlock({ src, alt }: { src: string; alt?: string }) {
  const safe = safeImageSrc(src)
  if (!safe) return <span className="image-blocked">{alt || 'billede blokeret'}</span>
  return <img src={safe} alt={alt ?? ''} loading="lazy" />
}
