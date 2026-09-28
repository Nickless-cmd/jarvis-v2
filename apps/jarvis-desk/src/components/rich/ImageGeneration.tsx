import { useEffect, useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { fetchBlobWithAuth, type ApiConfig } from '../../lib/api'
import { AttachmentBlock } from './AttachmentBlock'
import { KlikbartBillede } from './BilledLightbox'

type ImageBlock = Extract<ContentBlock, { type: 'image' }>

export function erBilledVaerktoej(name: string): boolean {
  return name === 'openrouter_image' || name === 'openrouter_image_edit' || name === 'pollinations_image'
}

/** Det eneste syns-værktøj i drift. `operator_screenshot` og
 *  `jarvis_browser_screenshot` TAGER billeder og er målt til ~0,1 s — de har
 *  intet at animere. */
export function erBilledAnalyse(name: string): boolean {
  return name === 'analyze_image'
}

/** Hvad der arbejdes på lige nu. To slags — de ligner ikke hinanden på
 *  skærmen, fordi de ikke er det samme arbejde. */
export type BilledArbejde =
  | { slags: 'generering' }
  /** `kilde` er navnet, til etiketten. `sti` er den FULDE sti — den er den
   *  eneste af de to der kan hentes, gennem `/visning/billede`. */
  | { slags: 'analyse'; kilde: string; sti: string }

/** Navnet på det billede der kigges på: sidste led af stien, ellers værten på
 *  en URL. Tom når kaldet ikke siger hvad det ser på — så står animationen
 *  uden navn frem for at gætte. */
export function billedKilde(input: Record<string, unknown> | undefined): string {
  const sti = typeof input?.image_path === 'string' ? input.image_path : ''
  if (sti) return sti.split(/[\\/]/).filter(Boolean).pop() ?? ''
  const url = typeof input?.image_url === 'string' ? input.image_url : ''
  if (!url) return ''
  try {
    return new URL(url).hostname
  } catch {
    return ''
  }
}

/** Den fulde sti til det billede der kigges på — kun når kaldet giver en
 *  absolut en. Ruten afviser alt andet, og så står rammen tom frem for at
 *  hente noget vi ikke må vise. */
export function billedSti(input: Record<string, unknown> | undefined): string {
  const sti = typeof input?.image_path === 'string' ? input.image_path : ''
  return sti.startsWith('/') ? sti : ''
}

type LevendeKald = { name: string; status?: string; input?: Record<string, unknown> }

/**
 * Det billedarbejde der kører LIGE NU blandt et sæt kald — eller null.
 *
 * Ét opslag, tre kaldesteder. Betingelsen stod før ordret tre steder, og da
 * `openrouter_image_edit` kom til, var det præcis den slags der bliver glemt
 * ét af stederne. Kører både en generering og en analyse i samme runde,
 * vinder den der står først — den blev startet først.
 */
export function levendeBilledArbejde(kald: LevendeKald[]): BilledArbejde | null {
  for (const k of kald) {
    if ((k.status ?? 'running') !== 'running') continue
    if (erBilledVaerktoej(k.name)) return { slags: 'generering' }
    if (erBilledAnalyse(k.name)) {
      return { slags: 'analyse', kilde: billedKilde(k.input), sti: billedSti(k.input) }
    }
  }
  return null
}

export function BilledArbejdeAnimation({ arbejde, config }: { arbejde: BilledArbejde; config?: ApiConfig }) {
  return arbejde.slags === 'analyse'
    ? <ImageAnalysisProgress kilde={arbejde.kilde} sti={arbejde.sti} config={config} />
    : <ImageGenerationProgress />
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

/**
 * Billedanalyse: en scanning hen over en ramme.
 *
 * Målt på CT105 27/9-2026 over fjorten dage: **232 kald, median 8,49 s,
 * p90 28,6 s**, 219 ok. Otte sekunder uden et tegn på liv er rigeligt til at
 * man tror turen er gået i stå — det er hele grunden til at den findes.
 *
 * Den ligner med vilje ikke genereringens prik-gitter. Gitteret siger «noget
 * bliver til»; scanningen siger «der bliver kigget på noget der allerede er».
 * Ingen procent, fordi backend ikke har nogen.
 */
export function ImageAnalysisProgress({ kilde, sti, config }: { kilde?: string; sti?: string; config?: ApiConfig }) {
  const navn = (kilde || '').trim()
  const [billede, setBillede] = useState<string | null>(null)

  // Det billede der bliver kigget på — hentet gennem den SAMME hvidlistede
  // rute som rækkevisningen bruger. Desk har ingen disk-adgang, og stien er
  // Jarvis' egen, ikke brugerens: et skærmbillede tages på serveren.
  useEffect(() => {
    setBillede(null)
    if (!config || !sti) return
    let afbrudt = false
    let objekt: string | null = null
    void (async () => {
      try {
        const blob = await fetchBlobWithAuth(config, `/visning/billede?sti=${encodeURIComponent(sti)}`)
        if (afbrudt) return
        objekt = URL.createObjectURL(blob)
        setBillede(objekt)
      } catch {
        // Uden for de hvidlistede rødder, eller netværket svigter: rammen står
        // tom, præcis som før. Navnet bærer resten.
      }
    })()
    return () => { afbrudt = true; if (objekt) URL.revokeObjectURL(objekt) }
  }, [config?.apiBaseUrl, config?.authToken, sti])

  return <div className="image-analysis" role="progressbar"
    aria-label={navn ? `Analyserer ${navn}` : 'Analyserer billede'}>
    <span className="image-analysis-label">
      Analyserer billede{navn ? <> · <span className="image-analysis-kilde">{navn}</span></> : null}…
    </span>
    <div className="image-analysis-ramme" aria-hidden="true">
      {billede ? <img className="image-analysis-billede" src={billede} alt="" /> : null}
      <span className="image-analysis-scan" />
      <span className="image-analysis-hjoerne tv" />
      <span className="image-analysis-hjoerne th" />
      <span className="image-analysis-hjoerne bv" />
      <span className="image-analysis-hjoerne bh" />
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
