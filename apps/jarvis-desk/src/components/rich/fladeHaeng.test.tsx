import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { MarkdownRenderer } from './MarkdownRenderer'
import { parseNativeRichSpec } from './NativeRichBlock'

/** MÅLT 30/10-2026 (Bjørn): «enten fejler fladerne ellers hænger de på flade
 *  forberedes». To forskellige fejl med samme overflade.
 *
 *  `state/flade_log.jsonl` (2.425 poster) viste fordelingen: 1.133 native,
 *  743 parse-null, 402 wrong-lang, 147 no-pre-node — altså 53 % der ikke blev
 *  en flade. Af de 743 parse-null var 672 afkortet JSON (harmløs
 *  streaming-støj), men **34 var fuldt gyldig JSON** der blev kastet væk af
 *  ÉN regel: hver række skulle have PRÆCIS `columns.length` values.
 *
 *  Og placeholderen havde ingen udgang: på en persisteret besked stod
 *  «flade forberedes…» for evigt og påstod at noget var i gang, når intet var.
 *
 *  Testene starter fra en HEL besked, ikke fra den isolerede JSON — samme
 *  lærepenge som `fladeMastForm.test.tsx`: en test på den isolerede blok kan
 *  ikke se hvordan markdown-laget leverer den. */

const TRE_KOLLONNER_TO_VALUES =
  '{"type":"comparison","title":"Hvordan en regel bliver efterlevet","columns":["Mekanisme","Virker den?","Bevis"],' +
  '"rows":[{"label":"Står i prompten som tekst","values":["Nej","læses som kontekst"]},' +
  '{"label":"Måles på det jeg faktisk skrev","values":["Ja","den eneste der bider"]}]}'

const HEL_BESKED = `## Sådan bliver en regel efterlevet

Tre mekanismer, målt:

\`\`\`jarvis-ui
${TRE_KOLLONNER_TO_VALUES}
\`\`\`

Det var pointen.`

// LUKKET fence med ugyldig JSON. En ÅBEN fence nås aldrig af `pre`-grenen —
// blok-opdelingen holder den tilbage til den er afsluttet, så en test på den
// form måler ingenting. Målt 30/10-2026: første udgave af denne test brugte
// netop den åbne form og fejlede på koden, ikke på sin egen antagelse.
const UGYLDIG_BLOK = `## Fladen der ikke blev færdig

\`\`\`jarvis-ui
{"type":"comparison","title":"Halvfærdig","columns":["A","B"],"rows":[{"label":"x","values":["1"]}
\`\`\`

Så langt nåede den.`

describe('flade — fejler eller hænger', () => {
  it('beholder en comparison hvor rækkerne mangler en celle (pad i stedet for kassér)', () => {
    const spec = parseNativeRichSpec(TRE_KOLLONNER_TO_VALUES)
    // FØR rettelsen: null, fordi ingen række havde præcis 3 values.
    expect(spec).not.toBeNull()
    expect(spec?.type).toBe('comparison')
    if (spec?.type === 'comparison') {
      expect(spec.columns).toHaveLength(3)
      expect(spec.rows).toHaveLength(2)
      // Den manglende tredje celle er tom — ikke årsag til at hele fladen dør.
      const foersteRaekke = spec.rows[0]
      expect(foersteRaekke).toBeDefined()
      expect(foersteRaekke?.values).toHaveLength(3)
      expect(foersteRaekke?.values[2]).toBe('')
    }
  })

  it('tegner fladen i en FÆRDIG besked i stedet for at vise en placeholder', () => {
    const { container } = render(<MarkdownRenderer text={HEL_BESKED} streaming={false} />)
    expect(container.textContent).not.toContain('flade forberedes')
    expect(container.querySelector('.native-comparison')).not.toBeNull()
    expect(container.textContent).toContain('Står i prompten som tekst')
  })

  it('viser IKKE «flade forberedes» på en færdig besked der aldrig kan blive en flade', () => {
    // Kernen i Bjørns klage: teksten stod der for evigt og løj om at noget
    // var i gang. På en færdig besked skal der stå hvad der faktisk skete.
    const { container } = render(<MarkdownRenderer text={UGYLDIG_BLOK} streaming={false} />)
    expect(container.textContent).not.toContain('flade forberedes')
    // Den tredje vej: en stille note — hverken spinner eller rå JSON.
    expect(container.querySelector('.flade-utilgaengelig')).not.toBeNull()
    expect(container.querySelector('pre')).toBeNull()
    // Prosaen omkring blokken er urørt; kun fladen selv blev en note.
    expect(container.textContent).toContain('Så langt nåede den.')
  })

})
