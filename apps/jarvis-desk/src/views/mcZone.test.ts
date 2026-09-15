import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Bjørn 15/9-2026: «Arbejde, Lektier og hans arbejdere ... de er bare kastet
 * ind i toppen og ikk som det andet».
 *
 * Målt i den ægte stilblok ved 1600px bredde, FØR:
 *
 *     .work-queue 1600   .lk 1600   .rv 1600   .aw 1600   .mc 1120 centreret
 *
 * `mc` var den eneste zone uden indpakning — alle andre går gennem `wrap()`.
 * De fire havde `max-width: none`, ingen auto-margin, og .lk/.rv/.aw havde
 * hverken baggrund, ramme eller polstring.
 *
 * Dette er en KILDE-vagt og ikke en layout-test: jsdom regner ikke CSS-layout,
 * så bredder kan ikke måles her. Den er svagere end målingen i en rigtig
 * browser, og det skal siges. Men den fanger det der ellers ville skride
 * tilbage: at indpakningen eller reglen forsvinder.
 */
const læs = (p: string) => fs.readFileSync(path.join(__dirname, '..', p), 'utf8')

describe('Arbejde-zonen har samme ramme som Mission Control', () => {
  it('zonen er pakket ind', () => {
    const v = læs('views/CoworkView.tsx')
    expect(v).toMatch(/case 'mc': return \(\s*<div className="mc-zone">/)
  })

  it('rammen findes i stilblokken', () => {
    expect(læs('styles/app.css')).toMatch(/\.mc-zone \{[^}]*flex-direction: column/)
  })

  it('bredden er MCs 1120 og ikke indstillingernes 720', () => {
    // 720 er den smalle indstillings-kolonne. Zonen står side om side med
    // Mission Control, så den skal følge MCs bredde.
    const css = læs('styles/app.css')
    const regel = css.slice(css.indexOf('.mc-zone > *'))
    expect(regel.slice(0, 120)).toContain('max-width: 1120px')
  })

  it('de fire sektioner får husets kort', () => {
    const css = læs('styles/app.css')
    const blok = css.slice(css.indexOf('.mc-zone > .work-queue'))
    for (const k of ['.lk', '.rv', '.aw']) {
      expect(blok.slice(0, 400)).toContain(`.mc-zone > ${k},`)
    }
    expect(blok.slice(0, 600)).toContain('border-radius: 10px')
  })

  it('Mission Control bliver liggende i zonen', () => {
    // Fjernes den, mister siden sit kontrolpanel — og testene ovenfor ville
    // stadig være grønne.
    const v = læs('views/CoworkView.tsx')
    const zone = v.slice(v.indexOf('<div className="mc-zone">'))
    expect(zone.slice(0, 600)).toContain('{missionControl}')
  })
})
