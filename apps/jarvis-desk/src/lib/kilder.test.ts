import { describe, it, expect } from 'vitest'
import { kilderFraBlokke, kilderPrDomaene } from './kilder'
import type { ContentBlock } from './sseProtocol'

const brug = (input: Record<string, unknown>, result?: string): ContentBlock =>
  ({ type: 'tool_use', id: 't1', name: 'web', input, result } as ContentBlock)

describe('kilder fra blokke', () => {
  it('finder adressen i et hentnings-KALD', () => {
    expect(kilderFraBlokke([brug({ url: 'https://www.dr.dk/nyt' })]))
      .toEqual([{ url: 'https://www.dr.dk/nyt', domaene: 'dr.dk' }])
  })

  it('finder adresser i det FOLDEDE resultat', () => {
    // foldToolResults lægger svaret i tool_use.result. Læser man kun input,
    // mister man alt fra en søgning — og det var halvdelen af kilderne.
    const b = [brug({ query: 'proxmox lxc' }, 'https://pve.proxmox.com/wiki/LXC og https://forum.proxmox.com/t/1')]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['pve.proxmox.com', 'forum.proxmox.com'])
  })

  it('svartekst tæller med — men efter det han faktisk hentede', () => {
    const b: ContentBlock[] = [
      { type: 'text', text: 'Jeg læste også https://citeret.dk/x' },
      brug({}, 'https://hentet.dk/y')
    ]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['hentet.dk', 'citeret.dk'])
  })

  it('hans eget maskineri er ikke en kilde', () => {
    const b = [brug({}, 'http://localhost:8080 http://10.0.0.39/x https://192.168.1.1 https://ude.dk/z')]
    expect(kilderFraBlokke(b).map((k) => k.domaene)).toEqual(['ude.dk'])
  })

  it('afsluttende tegnsætning hører ikke til adressen', () => {
    const b = [brug({}, 'Kilde: (https://dr.dk/nyt), samt https://tv2.dk/x.')]
    expect(kilderFraBlokke(b).map((k) => k.url)).toEqual(['https://dr.dk/nyt', 'https://tv2.dk/x'])
  })

  it('tom eller uden værktøjer giver ingen kilder', () => {
    expect(kilderFraBlokke([])).toEqual([])
    expect(kilderFraBlokke(null)).toEqual([])
    expect(kilderFraBlokke([{ type: 'text', text: 'ingen adresser her' }])).toEqual([])
  })

  it('samme adresse i både kald og svar tælles én gang', () => {
    expect(kilderFraBlokke([brug({ url: 'https://dr.dk/a' }, 'set på https://dr.dk/a')])).toHaveLength(1)
  })
})

describe('kompakt visning', () => {
  it('ét punkt pr. domæne, første URL vinder', () => {
    const k = kilderPrDomaene(kilderFraBlokke([brug({}, 'https://dr.dk/a https://dr.dk/b https://tv2.dk/c')]))
    expect(k.map((x) => x.domaene)).toEqual(['dr.dk', 'tv2.dk'])
    expect(k[0]!.url).toBe('https://dr.dk/a')
  })

  it('skærer ved maks, så en tung research-tur ikke fylder skærmen', () => {
    const mange = Array.from({ length: 30 }, (_, i) => `https://d${i}.dk/x`).join(' ')
    expect(kilderPrDomaene(kilderFraBlokke([brug({}, mange)]))).toHaveLength(8)
  })
})

describe('fund fra ÆGTE historik (7/9-2026)', () => {
  it('shell-syntaks klistret på en adresse hører ikke med', () => {
    // Målt: en bash-kommando gav domænet «apkcombo.com$(grep».
    expect(kilderFraBlokke([brug({ command: 'curl https://apkcombo.com/x$(grep -c y)' })])
      .map((k) => k.domaene)).toEqual(['apkcombo.com'])
  })

  it('hele 127-blokken er loopback', () => {
    expect(kilderFraBlokke([brug({}, 'http://127.0.0.1:8080 http://127.1.2.3 https://ude.dk')])
      .map((k) => k.domaene)).toEqual(['ude.dk'])
  })
})
