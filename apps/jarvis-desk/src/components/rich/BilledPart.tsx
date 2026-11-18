import { useContext } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { aspektCss } from '../../lib/medieVaerktoejer'
import { ImageBlock } from './ImageBlock'
import { AttachmentBlock } from './AttachmentBlock'
import { ImageGenerationProgress } from './ImageGeneration'
import { BilledGrid, type BilledGridFlise } from './BilledGrid'
import { WidgetPrompt } from './WidgetBlock'

type Part = Extract<ContentBlock, { type: 'image_generation_call' }>

/**
 * Et medie-kald som én plads i indholdet — fra kaldet starter til billedet
 * ligger der.
 *
 * ## Hvorfor den ikke er en animation ved siden af noget andet
 *
 * Indtil 18/11-2026 tegnede `BlocksRenderer` en `BilledArbejdeAnimation` ved
 * siden af værktøjslinjen, og billedet ankom senere som sin egen blok på et
 * nyt indeks — som `isDelivery` derefter flyttede til bunden. Det gav det hop
 * Bjørn beskrev som «billeder havner i top eller bund».
 *
 * Her er der ÉN plads. Den reserveres når kaldet starter, den fyldes når
 * billedet ankommer, og den flytter sig aldrig.
 *
 * ## Hvorfor højden er reserveret på to forskellige måder
 *
 * Målt 18/11-2026 på 171 gemte billeder: 42 % er 9:16, 20 % er 16:9, resten
 * fordeler sig på fire andre forhold. Der findes intet dominerende aspekt, så
 * et median-gæt ville være forkert i 58 % af tilfældene.
 *
 * - **Aspekt kendt** (kaldet oplyste `aspect_ratio`): reserver præcis højde
 *   fra forholdet. Nul hop, nul spild.
 * - **Aspekt ukendt**: reserver den MAKSIMALE højde i stedet for nul. Det ser
 *   ud som tom plads et øjeblik — men tom plads der forsvinder er et hop, og
 *   tom plads der bliver stående er ikke. Samme lære som blink 2: hoppet
 *   kommer fra relayoutet, ikke fra højden.
 */
export function BilledPart({ part }: { part: Part }) {
  const send = useContext(WidgetPrompt)
  const forhold = aspektCss(part.aspekt)
  const arbejder = part.status === 'running'
  const fejlet = part.status === 'error'
  const imageCount = part.billeder.length
  const brugerGrid = imageCount > 1 || (arbejder && part.forventet_antal > 1)
  const antalFliser = arbejder
    ? Math.max(part.forventet_antal, imageCount)
    : imageCount
  const fliser: BilledGridFlise[] = Array.from({ length: antalFliser }, (_, i) => {
    const billede = part.billeder[i]
    if (!billede) {
      return {
        key: `${part.id}-plads-${i}`,
        aspekt: part.aspekt,
        pladsholder: true,
        indhold: null,
      }
    }
    // Aspektet findes KUN paa parten, ikke paa det enkelte billede
    // (ContentBlock.billeder har src/alt/attachment_id/url/filename/mime_type).
    return {
      key: `${part.id}-${i}`,
      aspekt: part.aspekt,
      indhold: billede.src
        ? <ImageBlock src={billede.src} alt={billede.alt} />
        : <AttachmentBlock block={{ ...billede, type: 'image' }} />,
    }
  })

  const regenerer = () => {
    send?.(`[fra billedpart] Regenerér billedet fra værktøjskald ${part.id} med ${part.navn}.`)
  }

  return (
    <div
      className="billed-part"
      data-billed-part={part.id}
      data-status={part.status}
      data-aspekt={part.aspekt ?? 'ukendt'}
      data-image-count={imageCount}
      data-forventet-antal={part.forventet_antal}
    >
      {arbejder && part.forventet_antal > 1 ? (
        <div className="billed-part-billeder">
          <BilledGrid fliser={fliser} />
        </div>
      ) : arbejder ? (
        <div
          className="billed-part-plads"
          style={forhold ? { aspectRatio: forhold } : undefined}
        >
          <ImageGenerationProgress />
        </div>
      ) : null}

      {arbejder && part.forventet_antal > 1 ? (
        <span className="billed-part-taelling" aria-label="Genererede billeder">
          {imageCount}/{part.forventet_antal}
        </span>
      ) : null}

      {fejlet && part.billeder.length === 0 ? (
        <div className="billed-part-fejl" role="note">
          <span>Billedet kunne ikke genereres</span>
        </div>
      ) : null}

      {!arbejder && imageCount > 0 ? (
        <div className="billed-part-billeder">
          {brugerGrid
            ? <BilledGrid fliser={fliser} />
            : <div className="billed-part-enkelt">{fliser[0]?.indhold}</div>}
        </div>
      ) : null}

      {!arbejder ? (
        <button
          type="button"
          className="billed-part-regenerer"
          disabled={!send}
          onClick={regenerer}
        >
          Regenerér billede
        </button>
      ) : null}
    </div>
  )
}
