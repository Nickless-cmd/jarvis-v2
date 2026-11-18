import type { ContentBlock } from '../../lib/sseProtocol'
import { aspektCss } from '../../lib/medieVaerktoejer'
import { ImageBlock } from './ImageBlock'
import { AttachmentBlock } from './AttachmentBlock'
import { ImageGenerationProgress } from './ImageGeneration'

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
  const forhold = aspektCss(part.aspekt)
  const arbejder = part.status === 'running'
  const fejlet = part.status === 'error'

  return (
    <div
      className="billed-part"
      data-billed-part={part.id}
      data-status={part.status}
      data-aspekt={part.aspekt ?? 'ukendt'}
    >
      {arbejder ? (
        <div
          className="billed-part-plads"
          style={forhold ? { aspectRatio: forhold } : undefined}
        >
          <ImageGenerationProgress />
        </div>
      ) : null}

      {fejlet && part.billeder.length === 0 ? (
        <div className="billed-part-fejl" role="note">
          <span>Billedet kunne ikke genereres</span>
        </div>
      ) : null}

      {part.billeder.length > 0 ? (
        <div className="billed-part-billeder">
          {part.billeder.map((billede, i) => (
            billede.src
              ? <ImageBlock key={`${part.id}-${i}`} src={billede.src} alt={billede.alt} />
              // Persisteret form: kun en reference. `AttachmentBlock` henter
              // den med token — samme vej som en `image`-blok altid har brugt.
              : <AttachmentBlock
                  key={`${part.id}-${i}`}
                  block={{ ...billede, type: 'image' }}
                />
          ))}
        </div>
      ) : null}
    </div>
  )
}
