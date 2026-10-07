/**
 * Dialogerne skal ligge MIDT PÅ SKÆRMEN.
 *
 * Bjørn 4/10-2026: «når man klikker på privatliv & cookie bliver feltet vist
 * oppe i venstre hjørne istedet for midt på skærmen».
 *
 * Årsagen er ikke dialogen men `tokens.css` linje 179: `* { margin: 0 }`. Den
 * regel står i AUTHOR-origin, og origin vinder over specificitet — så den slår
 * UA'ens `dialog { margin: auto }`, selv om UA-reglen har en type-selektor og
 * reset'en har `*`. Uden `margin: auto` arver `dialog:modal` sin `inset: 0` og
 * lægger sig i øverste venstre hjørne.
 *
 * Denne test vogter begge dialoger, fordi de deler skæbne: bliver den ene
 * rettet og den anden glemt, ser det ud som om rettelsen virkede halvt. Det er
 * præcis den slags der er usynlig i en diff.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const laes = (n: string) => readFileSync(join(__dirname, n), 'utf8')

/** Reglen for én selektor, uden kommentarer der kan spise nabo-reglen.
 *  `[^{}]*` frem for `\s*` foran `{`: selektoren kan stå som FØRSTE led i en
 *  kommasepareret liste, og så kommer der flere selektorer før klammerne. */
const regel = (css: string, selektor: string) => {
  const ren = css.replace(/\/\*[\s\S]*?\*\//g, '')
  const m = ren.match(new RegExp(`${selektor}[^{}]*\\{([^}]*)\\}`))
  return m?.[1] ?? ''
}

const MIDT = [
  ['position', /position:\s*fixed/],
  ['inset', /inset:\s*0/],
  ['margin', /margin:\s*auto/],
] as const

describe('dialogerne ligger midt på skærmen', () => {
  it('privatliv-dialogen nulstiller margin-resetten', () => {
    const r = regel(laes('privacy-dialog.css'), '\\.privacy-dialog')
    for (const [navn, m] of MIDT) expect(r, `mangler ${navn}`).toMatch(m)
  })

  it('fejl-rapporten bærer samme vaern', () => {
    const r = regel(laes('bug-rapport.css'), '\\.bug-rapport')
    for (const [navn, m] of MIDT) expect(r, `mangler ${navn}`).toMatch(m)
  })
})
