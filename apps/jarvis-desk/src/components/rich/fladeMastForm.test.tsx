import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { enforceStructure } from '../../lib/enforceStructure'

/** MÅLT 25/10-2026 (side-2430432a89): 58 af 59 `wrong-lang`-poster i
 *  `state/flade_log.jsonl` havde JSON'en på fence-markørens EGEN linje.
 *  I CommonMark bliver resten af linjen en del af info-stringen, så `lang`
 *  bliver `jarvis-ui` men `code` bliver TOM — og fladen falder tilbage til en
 *  tom kodeblok.
 *
 *  Denne test starter fra en HEL besked (overskrift + prosa + fence + JSON),
 *  som den Bjørn faktisk fik. En test på den isolerede JSON-blok kan ikke
 *  finde fejlen — den er allerede grøn. */

const SPEC = '{"type":"comparison","title":"Ruten er levende","columns":["Svar","Hvad det beviser"],"rows":[{"label":"/cowork/side-tasks","values":["200","ruten findes"]}]}'

const HEL_BESKED_MAST = `## ✅ Ruten er levende — og det tog to kald at bevise

Uvicorn startede **16:53:04**, efter både \`cowork.py\` (16:26) og commit \`f2e40773e\` (16:52:03).

\`\`\`jarvis-ui ${SPEC}
\`\`\`

Og lidt prosa bagefter.`

const HEL_BESKED_KORREKT = `## ✅ Ruten er levende — og det tog to kald at bevise

Uvicorn startede **16:53:04**, efter både \`cowork.py\` (16:26) og commit \`f2e40773e\` (16:52:03).

\`\`\`jarvis-ui
${SPEC}
\`\`\`

Og lidt prosa bagefter.`

describe('flade-render — mast fence-form', () => {
  it('en HEL besked med JSON på markørens linje rendres som native flade', () => {
    const { container } = render(<MarkdownRenderer text={HEL_BESKED_MAST} streaming={false} />)
    expect(container.querySelectorAll('.native-rich')).toHaveLength(1)
    expect(container.querySelectorAll('.chat-codeblock')).toHaveLength(0)
    // Indholdet skal være der — ikke bare containeren.
    expect(container.textContent).toContain('/cowork/side-tasks')
    expect(container.textContent).toContain('ruten findes')
  })

  it('den korrekte form giver samme resultat — reparationen må ikke ændre en gyldig blok', () => {
    const { container } = render(<MarkdownRenderer text={HEL_BESKED_KORREKT} streaming={false} />)
    expect(container.querySelectorAll('.native-rich')).toHaveLength(1)
    expect(container.querySelectorAll('.chat-codeblock')).toHaveLength(0)
  })

  it('en allerede korrekt fence røres ikke af enforceStructure', () => {
    expect(enforceStructure(HEL_BESKED_KORREKT)).toBe(HEL_BESKED_KORREKT)
  })

  it('prosa og overskrift bevares — kun fence-linjen ændres', () => {
    const ud = enforceStructure(HEL_BESKED_MAST)
    expect(ud).toContain('## ✅ Ruten er levende')
    expect(ud).toContain('Uvicorn startede **16:53:04**')
    expect(ud).toContain('Og lidt prosa bagefter.')
    expect(ud).toContain('```jarvis-ui\n' + SPEC)
  })

  it('en fence med et andet sprog røres ikke', () => {
    const ts = '```ts\nconst a = 1\n```'
    expect(enforceStructure(ts)).toBe(ts)
  })

  it('en bar jarvis-ui uden hegn røres ikke her — det er guardens opgave', () => {
    const bar = `jarvis-ui ${SPEC}`
    expect(enforceStructure(bar)).toBe(bar)
  })

  // MÅLT 25/10-2026: denne form fandtes i de poster min første udgave IKKE
  // rettede — lukke-fencen stod på SAMME linje som JSON'ens slutning
  // (`}]} ``` `), så regex'en der krævede at JSON'en sluttede linjen sprang
  // den over. Den er lige så ugyldig som formen uden lukke-fence.
  it('lukke-fence på SAMME linje som JSON-slutningen rettes også', () => {
    const mast = `## Overskrift\n\nProsa.\n\n\`\`\`jarvis-ui ${SPEC} \`\`\`\n\nEfter.`
    const ud = enforceStructure(mast)
    expect(ud).toContain('```jarvis-ui\n' + SPEC + '\n```')
    expect(ud).toContain('## Overskrift')
    expect(ud).toContain('Efter.')
    const { container } = render(<MarkdownRenderer text={mast} streaming={false} />)
    expect(container.querySelectorAll('.native-rich')).toHaveLength(1)
    expect(container.querySelectorAll('.chat-codeblock')).toHaveLength(0)
  })

  // En uafsluttet blok (streaming midt i JSON'en) må IKKE røres: der er intet
  // at flytte endnu, og et halvt JSON-objekt ville blive ødelagt af et indgreb.
  it('en uafsluttet blok lades urørt', () => {
    const halv = '## Overskrift\n\n```jarvis-ui {"type":"stats","items":[{"label"'
    expect(enforceStructure(halv)).toBe(halv)
  })
})
