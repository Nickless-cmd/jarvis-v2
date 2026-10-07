import { PixelRatio, StyleSheet } from 'react-native'
import { fireEvent, render } from '@testing-library/react-native'
import { GlidendeTekst, SWEEP_ANDEL, banen } from './GlidendeTekst'

jest.mock('../lib/useReducedMotion', () => ({ useReducedMotion: () => mockReduced }))
let mockReduced = false
beforeEach(() => { mockReduced = false })

it('teksten staar som ÉT stykke — ikke delt op pr. bogstav', async () => {
  // Foerste udgave delte den, og saa ville en skaermlaeser laese linjen
  // bogstav for bogstav og tekst-opslag fejle.
  const s = await render(<GlidendeTekst text="Tænker…" aktiv />)
  expect(s.getByText('Tænker…')).toBeTruthy()
})

it('INAKTIV har intet lys', async () => {
  const s = await render(<GlidendeTekst text="Tænkte i 9 s" aktiv={false} />)
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
  expect(s.getByText('Tænkte i 9 s')).toBeTruthy()
})

it('reduceret bevaegelse slaar lyset FRA — men teksten bliver', async () => {
  // En animation man har bedt systemet om at lade vaere med, er ikke en
  // effekt; det er en overtraedelse.
  mockReduced = true
  const s = await render(<GlidendeTekst text="Tænker…" aktiv />)
  // MAAL BREDDEN FOERST. Uden den er baandet vaek alligevel (bredde 0), og
  // testen ville bestaa uanset om reduced-motion blev respekteret - den
  // mutation slap netop igennem.
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
  expect(s.getByText('Tænker…')).toBeTruthy()
})

it('lyset venter paa at bredden er MAALT', async () => {
  // Uden maalingen ville baandet enten staa stille eller skyde forbi kanten
  // paa en linje af ukendt laengde.
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
})

it('naar bredden er maalt, glider lyset', async () => {
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  // `onLayout` sidder paa den YDRE View, ikke paa teksten.
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  // `includeHiddenElements`: baandet er skjult for tilgaengelighed, og RNTL
  // udelader skjulte elementer som standard. At det SKAL med her, er i sig
  // selv beviset for at skjulningen virker.
  expect(s.getByTestId('glidende-lys', { includeHiddenElements: true })).toBeTruthy()
})

it('lyset kan ikke trykkes paa og laeses ikke op', async () => {
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  const lys = s.getByTestId('glidende-lys', { includeHiddenElements: true })
  expect(lys.props.pointerEvents).toBe('none')
  expect(lys.props.accessibilityElementsHidden).toBe(true)
})

it('lys og grundfarve bruger samme synlige tekstmaske', async () => {
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  const lys = s.getByTestId('glidende-lys', { includeHiddenElements: true })
  expect(lys).toBeTruthy()
  expect(s.getByText('Kører bash…')).toBeTruthy()
})

/* ── DSH-rytmen (30/9-2026) ─────────────────────────────────────────────────
 *
 * Bjørn valgte DSH's shimmer til desk og bad om den samme på mobilen: «det er
 * stadig den sløve». Vores var ét kontinuert sweep på 2.250 ms; DSH's er
 * 300 ms opstart, 1 s sweep, 500 ms hvile.
 *
 * Forskellen er ikke farten — den er at der ER en pause. Derfor måles der på
 * hvor båndet FAKTISK står gennem omløbet, ikke på varigheden alene: en kortere
 * varighed uden plateau er bare et hurtigere kontinuert sweep.
 */
describe('DSH-rytmen', () => {
  const BREDDE = 200
  const BAAND = 90

  const vis = async () => {
    const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
    await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
      { nativeEvent: { layout: { width: BREDDE, height: 20 } } })
    return s
  }

  /** Båndets translateX, læst ud af det rendrede træ. */
  const hvor = (s: ReturnType<typeof render> extends Promise<infer T> ? T : never): number => {
    const j = JSON.stringify(s.toJSON())
    const m = /"transform":\[\{"translateX":(-?[\d.]+)\}\]/.exec(j)
    if (!m) throw new Error('fandt ingen translateX i træet')
    return Number(m[1])
  }

  it('sweepet fylder to tredjedele af omløbet — resten er hvile', () => {
    // 1 s af 1,5 s. Står den på 1, er der ingen pause overhovedet.
    expect(SWEEP_ANDEL).toBeCloseTo(1000 / 1500, 4)
    expect(SWEEP_ANDEL).toBeLessThan(1)
  })

  it('SELVE BANEN har et plateau — konstanten alene beviser ingenting', () => {
    // Mutationskørsel: at fjerne plateauet fra interpolationen lod alle
    // elleve tests bestå, fordi de kun læste konstanten. Banen er derfor
    // skilt ud som en ren funktion, og det er DEN der måles her.
    const b = banen(BREDDE)
    expect(b.inputRange).toEqual([0, SWEEP_ANDEL, 1])
    // De to sidste udgangsværdier er ENS — det ER pausen.
    expect(b.outputRange[1]).toBe(b.outputRange[2])
  })

  it('banen begynder og ender uden for teksten', () => {
    const b = banen(BREDDE)
    expect(b.outputRange[0]).toBeLessThanOrEqual(-BAAND)   // højre kant på 0
    expect(b.outputRange[1]).toBeGreaterThanOrEqual(BREDDE) // venstre kant på bredden
  })

  it('banen følger bredden — ikke et fast tal', () => {
    // En hardkodet slutposition ville ramme forkert på en kort linje.
    expect(banen(100).outputRange[1]).toBeLessThan(banen(400).outputRange[1]!)
  })

  it('båndet starter HELT uden for teksten til venstre', async () => {
    // Båndet er 90 bredt; ved -90 er dets højre kant præcis på 0.
    const s = await vis()
    expect(hvor(s)).toBe(-BAAND)
  })

  it('og ender HELT uden for teksten til højre', async () => {
    // `outputRange`s anden værdi. Sammen med den forrige er det dét desk
    // manglede: dér var gradienten brolagt, så et nyt bånd altid var på vej ind.
    const s = await vis()
    const j = JSON.stringify(s.toJSON())
    expect(j).toContain(`"width":${BAAND}`)          // ét bånd, fast bredde
    expect(hvor(s)).toBeLessThanOrEqual(0)
  })

  it('der er ÉN maske og ÉT bånd — ingen brolægning', async () => {
    // Desks fejl var `background-repeat: repeat`. Her er der én `Rect` i
    // den animerede gruppe, og den kan ikke gentages.
    const s = await vis()
    const j = JSON.stringify(s.toJSON())
    expect((j.match(/url\(#lysboelge\)/g) ?? [])).toHaveLength(1)
    expect((j.match(/url\(#bogstaver\)/g) ?? [])).toHaveLength(1)
  })
})

/** Alle `fontSize`-tal i traeet, oppefra og ned. Den synlige SVG-maske er den
 *  eneste der baerer skriften som PROP — den skjulte native tekst har den i
 *  sin stil, og den er alligevel usynlig. */
const skrifter = (node: unknown, ud: number[] = []): number[] => {
  if (node == null || typeof node === 'string') return ud
  if (Array.isArray(node)) { node.forEach((n) => skrifter(n, ud)); return ud }
  const n = node as { props?: Record<string, unknown>; children?: unknown }
  if (typeof n.props?.fontSize === 'number') ud.push(n.props.fontSize)
  skrifter(n.children, ud)
  return ud
}

/** Tegn lyset med en given system-skala og giv maskens skrift tilbage. */
const medSkala = async (skala: number): Promise<number[]> => {
  const spy = jest.spyOn(PixelRatio, 'getFontScale').mockReturnValue(skala)
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv style={{ fontSize: 15 }} />)
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  const tal = skrifter(s.toJSON())
  spy.mockRestore()
  return tal
}

it('lyset tegnes i SAMME stoerrelse som den native tekst — ogsaa naar systemet skalerer', async () => {
  // Indtil 26/9-2026 var lyset bygget af NATIVE tekstlag og skalerade derfor
  // med grundteksten. Codex' SVG-maske (763bb23a0) tegner selv bogstaverne —
  // og SVG kender ikke systemets skrift-skala. Uden korrektionen stod den
  // KOERENDE linje i 15 dp mens den FAERDIGE stod i 15 x skalaen, saa den
  // koerende sa STOERRE ud end den faerdige. (Bjørn 30/9-2026: «tekst
  // stoerrelsen er for stor mens runden koere … men naar runden er forbi
  // aendrer teksten til normal stoerrelse».)
  expect((await medSkala(0.85)).at(-1)).toBeCloseTo(12.75, 6)
})

it('med skala 1 tegnes lyset i praecis den skrift stilen beder om', async () => {
  // Kontrollen: korrektionen maa ikke aendre noget naar systemet ikke skalerer.
  expect((await medSkala(1)).at(-1)).toBe(15)
})
