import { render } from '@testing-library/react-native'
import { CodeTitle } from './CodeTitle'
import type { GitStatus } from '../lib/apiClient'

const g = (o: Partial<GitStatus> = {}): GitStatus => ({
  branch: 'main', dirty: 0, added: 0, removed: 0, isGit: true,
  repo: 'jarvis-v2', host: 'CheifOne', link: 'ok', ...o,
})

it('viser hvilket repo paa hvilken maskine', async () => {
  const screen = await render(<CodeTitle titel="Diagnose WLED" git={g()} />)
  expect(screen.getByText('Diagnose WLED')).toBeTruthy()
  expect(screen.getByText('jarvis-v2')).toBeTruthy()
  expect(screen.getByText('CheifOne')).toBeTruthy()
})

it('forbundet er GROEN', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'ok' })} />)
  expect(screen.getByTestId('link-ok')).toBeTruthy()
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-ok').props.style).backgroundColor)
    .toBe('#4CAF50')
})

it('GENFORBINDER er gul, ikke roed', async () => {
  // En desk der genstarter staar registreret et oejeblik endnu. Roedt hver
  // gang nogen genstartede sin app ville laere én at se bort fra farven.
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'genforbinder' })} />)
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-genforbinder').props.style).backgroundColor)
    .toBe('#FFB347')
})

it('ingen forbindelse er ROED', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'nede' })} />)
  const { StyleSheet } = require('react-native')
  expect(StyleSheet.flatten(screen.getByTestId('link-nede').props.style).backgroundColor)
    .toBe('#ff8080')
})

it('de tre farver er FORSKELLIGE — ellers siger prikken ingenting', async () => {
  const { StyleSheet } = require('react-native')
  const farve = async (link: GitStatus['link']) => {
    const s = await render(<CodeTitle titel="x" git={g({ link })} />)
    return StyleSheet.flatten(s.getByTestId(`link-${link}`).props.style).backgroundColor
  }
  // ÉN render pr. kald ville normalt braekke oprydningen; her hentes farven
  // og traeet forlades med det samme, og RNTL rydder mellem tests - saa det
  // er ét trae ad gangen paa naer i selve loekken. Derfor laeses vaerdien FOER
  // naeste render.
  const a = await farve('ok')
  const b = await farve('genforbinder')
  const c = await farve('nede')
  expect(new Set([a, b, c]).size).toBe(3)
})

it('prikken siger ogsaa sin tilstand med ord', async () => {
  const screen = await render(<CodeTitle titel="x" git={g({ link: 'genforbinder' })} />)
  expect(screen.getByLabelText('Genforbinder')).toBeTruthy()
})

it('UDEN git-status er der ingen kontekstlinje', async () => {
  const screen = await render(<CodeTitle titel="x" git={null} />)
  expect(screen.queryByTestId('link-ok')).toBeNull()
  expect(screen.getByText('x')).toBeTruthy()
})

it('titel-pillen har et BREDDE-loft — den maa ikke vokse med navnet', async () => {
  // Bjoern 28/9-2026: «i header feltet(badge) der holder session navn skal
  // have en fast stoerrelse. Ikke stoerre end feltet(badge) i hoejre side af
  // header». Hoejden var laast siden 12/9; det var BREDDEN der loeb — maalt
  // 229 dp mod hoejre pilles 106. Uden loftet skubber et langt navn bjaelken.
  const { StyleSheet } = require('react-native')
  const lang = 'Hvad er den samlet status paa cheaplane og hvordan ser det ud'
  const screen = await render(<CodeTitle titel={lang} git={g()} />)
  const flad = StyleSheet.flatten(screen.getByTestId('code-titel').props.style)
  expect(flad.maxWidth).toBe(142)
})

it('loftet laeses fra badgeGeometri — ikke skrevet to steder', () => {
  // Et tal skrevet to steder passer kun indtil nogen aendrer det ene. Samme
  // regel som for hoejden: begge skal laeses fra badgeGeometri.
  const fs = require('fs'); const path = require('path')
  const l = (f: string) => fs.readFileSync(path.join(__dirname, f), 'utf8')
  expect(l('CodeTitle.tsx')).toMatch(/maxWidth: BADGE_MAKS_B/)
  expect(l('badgeGeometri.ts')).toMatch(/export const BADGE_MAKS_B = 142/)
})

it('kontekst-linjen maa SKRUMPE — ellers flyder den ud over kanten', () => {
  // Selve mekanismen bag Bjoerns anden melding 28/9-2026: «indholdet stikker
  // ud over». Boernene i pillen havde flexShrink 0 (RN's standard), saa da
  // loftet blev sat under deres naturlige bredde, voksede de forbi deres far i
  // stedet for at klippe sig selv. Et loft uden skrump er ikke et loft.
  const fs = require('fs'); const path = require('path')
  const kilde = fs.readFileSync(path.join(__dirname, 'CodeTitle.tsx'), 'utf8')
  const raekke = kilde.split('kontekst: {')[1].split('}')[0]
  expect(raekke).toMatch(/flexShrink: 1/)
  expect(raekke).toMatch(/minWidth: 0/)
  const meta = kilde.split('meta: {')[1].split('}')[0]
  expect(meta).toMatch(/flexShrink: 1/)
})

it('prikken maa IKKE skrumpe — den er kun 6 dp', () => {
  // Skrump skal ramme TEKSTEN, ikke den lille prik der forsvinder hvis den
  // faar lov at give sig.
  const fs = require('fs'); const path = require('path')
  const kilde = fs.readFileSync(path.join(__dirname, 'CodeTitle.tsx'), 'utf8')
  expect(kilde.split('prik: {')[1].split('}')[0]).toMatch(/flexShrink: 0/)
})
