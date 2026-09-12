import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * Vagt mod mønsteret der ikke virker.
 *
 * MÅLT 12/9-2026 på telefonen: `<Image source={{uri, headers}}>` mod en
 * beskyttet rute gav 401 på alle fire billeder — serveren så anmodningen uden
 * Authorization — mens listningen af de SAMME billeder med det SAMME token
 * gik igennem. React Natives billed-loader dropper headeren.
 *
 * Ingen enhedstest kan se det: en test der selv leverer billedet henter
 * aldrig noget. Derfor læses kilden i stedet. Vagten er billig og fanger
 * præcis den ene fejl der kostede en runde på enheden.
 */
// Kommentarer stripes FOERST. Foerste udgave af vagten var roed paa
// MessageAttachments fordi den matchede sin egen advarsel om moensteret -
// en test der anklager beskrivelsen af fejlen i stedet for fejlen.
const kilde = (sti: string) =>
  readFileSync(join(__dirname, '..', sti), 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/[^\n]*/g, '')

const MISTAENKT = /source=\{\{\s*uri[^}]*headers/s

it('BillederScreen bruger ikke det moenster der taber sin header', () => {
  expect(kilde('screens/BillederScreen.tsx')).not.toMatch(MISTAENKT)
})

it('MessageAttachments gjorde det FOER — og goer det ikke laengere', () => {
  expect(kilde('components/MessageAttachments.tsx')).not.toMatch(MISTAENKT)
})

it('ogsaa fuldskaerms-visningen tabte sin header', () => {
  expect(kilde('components/FullscreenImagePreview.tsx')).not.toMatch(MISTAENKT)
  expect(kilde('components/FullscreenImagePreview.tsx')).toMatch(/<AuthImage/)
})

it('begge henter i stedet gennem AuthImage', () => {
  expect(kilde('screens/BillederScreen.tsx')).toMatch(/<AuthImage/)
  expect(kilde('components/MessageAttachments.tsx')).toMatch(/<AuthImage/)
})

it('AuthImage sender faktisk et Bearer-token med', () => {
  const src = kilde('components/AuthImage.tsx')
  expect(src).toMatch(/headers: config\.authToken \? \{ Authorization: `Bearer \$\{config\.authToken\}` \}/)
  // ... og genbruger den lokale kopi frem for at hente igen ved hver rulning.
  expect(src).toMatch(/if \(info\.exists && \(info\.size \?\? 0\) > 0\) return dest/)
})
