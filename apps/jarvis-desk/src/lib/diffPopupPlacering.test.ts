import { describe, it, expect } from 'vitest'
import { beregnDiffPlacering, type Kant } from './diffPopupPlacering'

/**
 * Bjoerns sag 29/9-2026: diffen lagde sig hen over SIDEPANELET, fordi den
 * spejlede til venstre naar der ikke var plads til hoejre — og maalte plads
 * mod hele vinduet. Rammen er nu chat-fladen.
 */

// Et typisk vindue: sidepanel 0-260, chat 260-1400.
const CHAT: Kant = { top: 0, bottom: 900, left: 260, right: 1400 }
const VINDUE = { bredde: 1400, hoejde: 900 }
const HOEJDE = 420

const placer = (raekke: Kant, ramme = CHAT, vindue = VINDUE) =>
  beregnDiffPlacering({ raekke, ramme, vindue, hoejde: HOEJDE })

describe('hover-diffens placering', () => {
  it('daekker ALDRIG sidepanelet — heller ikke naar raekken staar yderst til hoejre', () => {
    // Praecis hans sag: ingen plads til hoejre, saa den gamle kode spejlede
    // til venstre og landede paa 1340-560-10 = 770 ... nej: raekken laa
    // laengere inde, og resultatet blev negativt/over panelet.
    const p = placer({ top: 300, bottom: 320, left: 300, right: 1380 })
    expect(p.left).toBeGreaterThanOrEqual(CHAT.left)
    expect(p.left + p.bredde).toBeLessThanOrEqual(CHAT.right)
  })

  it('staar til hoejre for raekken naar der er plads', () => {
    const p = placer({ top: 100, bottom: 120, left: 300, right: 500 })
    expect(p.left).toBe(510)
    expect(p.opad).toBe(false)
  })

  it('spejles til venstre for raekken naar der ikke er plads til hoejre', () => {
    const p = placer({ top: 100, bottom: 120, left: 900, right: 1100 })
    // 1100+10+560 = 1670 > 1392 → venstre: 900-560-10 = 330, inde i chatten.
    expect(p.left).toBe(330)
  })

  it('en raekke naer bunden vender popup\'en OPAD og holder den hos raekken', () => {
    const raekke = { top: 820, bottom: 840, left: 300, right: 500 }
    const p = placer(raekke)
    expect(p.opad).toBe(true)
    // Bunden staar ved raekkens bund — ikke bare skubbet op i en klump.
    expect(p.top + HOEJDE).toBe(raekke.bottom)
  })

  it('en raekke naer TOPPEN bliver nedad — vendingen er betinget, ikke fast', () => {
    const p = placer({ top: 40, bottom: 60, left: 300, right: 500 })
    expect(p.opad).toBe(false)
    expect(p.top).toBe(40)
  })

  it('en lav skaerm KRYMPER popup\'en i stedet for at lade den stikke ud', () => {
    // 430 px skaerm, 420 px popup: ingen vending hjaelper. Kroppen scroller
    // allerede, saa den skal vaere lavere — ikke staa halvt uden for.
    const p = placer({ top: 200, bottom: 220, left: 300, right: 500 },
                     CHAT, { bredde: 1400, hoejde: 430 })
    expect(p.hoejde).toBe(430 - 16)
    expect(p.top).toBeGreaterThanOrEqual(8)
    expect(p.top + p.hoejde).toBeLessThanOrEqual(430 - 8)
  })

  it('en hoej nok skaerm roerer ikke hoejden', () => {
    const p = placer({ top: 100, bottom: 120, left: 300, right: 500 })
    expect(p.hoejde).toBe(HOEJDE)
  })

  it('en smal chat-flade giver en smallere popup, ikke en der stikker ud', () => {
    const smal: Kant = { top: 0, bottom: 900, left: 260, right: 600 }
    const p = placer({ top: 100, bottom: 120, left: 300, right: 500 }, smal)
    expect(p.bredde).toBeLessThanOrEqual(smal.right - smal.left - 16)
    expect(p.left).toBeGreaterThanOrEqual(smal.left)
    expect(p.left + p.bredde).toBeLessThanOrEqual(smal.right)
  })

  it('rammen er chat-fladen og IKKE vinduet — det var hele fejlen', () => {
    // Samme raekke, to rammer. Maalt mod vinduet ville venstre kant kunne gaa
    // helt ud til 8; maalt mod chatten kan den ikke komme forbi 268.
    const raekke = { top: 300, bottom: 320, left: 280, right: 1380 }
    const medChat = placer(raekke)
    const medVindue = placer(raekke, { top: 0, bottom: 900, left: 0, right: 1400 })
    expect(medVindue.left).toBeLessThan(CHAT.left)
    expect(medChat.left).toBeGreaterThanOrEqual(CHAT.left)
  })
})
