import { useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { AttachmentBlock } from './AttachmentBlock'
import { KlikbartBillede } from './BilledLightbox'

type ImageBlock = Extract<ContentBlock, { type: 'image' }>

export function erBilledVaerktoej(name: string): boolean {
  return name === 'openrouter_image' || name === 'openrouter_image_edit' || name === 'pollinations_image'
}

/** Backend giver ingen procent; prikkerne viser kun at kaldet stadig kører. */
export function ImageGenerationProgress() {
  return <div className="image-generation" role="progressbar" aria-label="Genererer billede">
    <span className="image-generation-label">Genererer billede…</span>
    <div className="image-generation-grid" aria-hidden="true">
      {Array.from({ length: 16 * 16 }, (_, i) => <i key={i} style={{ opacity: Math.max(0.14, 0.85 - Math.hypot(i % 16 - 7.5, Math.floor(i / 16) - 7.5) * 0.08) }} />)}
    </div>
  </div>
}

export function GeneratedImageGallery({ images }: { images: ImageBlock[] }) {
  const [selected, setSelected] = useState(0)
  const active = images[Math.min(selected, images.length - 1)]
  if (!active) return null
  const render = (image: ImageBlock, miniature = false, onSelect?: () => void) => {
    const name = image.filename || image.alt || 'billede'
    return image.src
      ? <KlikbartBillede src={image.src} alt={name} className={miniature ? 'generated-thumbnail' : 'generated-main'} onSelect={onSelect} />
      : <AttachmentBlock block={{ ...image, type: 'image' }} onImageSelect={onSelect}
          imageClassName={miniature ? 'generated-thumbnail' : 'generated-main'} />
  }
  return <div className="generated-gallery" data-testid="generated-image-gallery">
    {render(active)}
    <div className="generated-choices" aria-label="Billedvalg">
      {images.map((image, i) => <span key={image.attachment_id || image.src || i} className={i === selected ? 'selected' : ''}>
        {render(image, true, () => setSelected(i))}
      </span>)}
    </div>
  </div>
}
