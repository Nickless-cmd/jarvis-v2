import { describe, expect, it } from 'vitest'
import { parseXrandrMonitors, skærmOversigt } from './skaerme'

/** Bjørns faktiske svar fra `xrandr --listmonitors`, målt 21/9-2026.
 *
 *  Læg mærke til at xrandr's egen nummerering IKKE følger skrivebordet:
 *  `0: DP-0` er den MIDTERSTE skærm (x=1920), mens `1: DP-4` står længst til
 *  venstre (x=0). Det er hele grunden til at `skærmOversigt` sorterer. */
const XRANDR_BJOERN = `Monitors: 3
 0: +*DP-0 1920/597x1080/336+1920+0  DP-0
 1: +DP-4 1920/531x1080/299+0+0  DP-4
 2: +DP-2 1920/531x1080/299+3840+0  DP-2
`

describe('parseXrandrMonitors', () => {
  it('laeser Bjoerns tre skaerme med rigtige bounds', () => {
    const skærme = parseXrandrMonitors(XRANDR_BJOERN)
    expect(skærme).not.toBeNull()
    expect(skærme).toHaveLength(3)
    expect(skærme!.map((s) => [s.navn, s.x, s.width])).toEqual([
      ['DP-0', 1920, 1920],
      ['DP-4', 0, 1920],
      ['DP-2', 3840, 1920],
    ])
  })

  it('markerer den primaere skaerm — stjernen i flagene', () => {
    const skærme = parseXrandrMonitors(XRANDR_BJOERN)!
    expect(skærme.filter((s) => s.primaer).map((s) => s.navn)).toEqual(['DP-0'])
  })

  it('taaler en skaerm sat til venstre for den primaere (negativ x)', () => {
    const ud = `Monitors: 2
 0: +*HDMI-0 1920/531x1080/299+0+0  HDMI-0
 1: +DP-1 1920/531x1080/299+-1920+0  DP-1
`
    const skærme = parseXrandrMonitors(ud)
    expect(skærme!.map((s) => s.x)).toEqual([0, -1920])
  })

  it('giver null naar formatet ikke passer — saa kalderen ved det', () => {
    expect(parseXrandrMonitors('Monitors: 0\n')).toBeNull()
    expect(parseXrandrMonitors('')).toBeNull()
    expect(parseXrandrMonitors('xrandr: command not found')).toBeNull()
  })
})

describe('skærmOversigt', () => {
  it('nummererer fra venstre, saa skaerm 1 er den laengst til venstre', () => {
    const oversigt = skærmOversigt(parseXrandrMonitors(XRANDR_BJOERN)!)
    expect(oversigt.map((s) => [s.indeks, s.navn])).toEqual([
      [1, 'DP-4'],
      [2, 'DP-0'],
      [3, 'DP-2'],
    ])
  })

  it('giver et midtpunkt Jarvis kan sigte efter', () => {
    const oversigt = skærmOversigt(parseXrandrMonitors(XRANDR_BJOERN)!)
    expect(oversigt.map((s) => s.midtpunkt)).toEqual([
      { x: 960, y: 540 },
      { x: 2880, y: 540 },
      { x: 4800, y: 540 },
    ])
  })

  it('bevarer hvilken skaerm der er den primaere', () => {
    const oversigt = skærmOversigt(parseXrandrMonitors(XRANDR_BJOERN)!)
    expect(oversigt.find((s) => s.primaer)?.navn).toBe('DP-0')
  })

  it('giver en tom liste for tom input i stedet for at kaste', () => {
    expect(skærmOversigt([])).toEqual([])
  })
})
