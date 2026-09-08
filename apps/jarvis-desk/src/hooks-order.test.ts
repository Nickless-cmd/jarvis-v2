import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Et hook må aldrig stå efter en betinget return.
 *
 * 8/9-2026 lagde jeg et `useMemo` under `if (!settings) return null` i App.tsx.
 * Så længe settings var null kørte hooket ikke; så snart de ankom, gjorde det.
 * React tæller hooks pr. render, og hele visningen faldt med
 *
 *     Minified React error #310 — Rendered more hooks than during the
 *     previous render
 *
 * Buildet var grønt, alle 605 tests var grønne, og appen var ubrugelig.
 *
 * Den rigtige vagt er eslint-plugin-react-hooks (`rules-of-hooks`), men den er
 * ikke installeret her og `npm run lint` peger på en config der ikke findes.
 * Indtil den er sat op, fanger denne test klassen: en tidlig `return` på
 * funktions-niveau (to mellemrums indrykning) efterfulgt af et hook på samme
 * niveau i samme fil.
 */

const ROD = join(__dirname)
const HOOK = /^ {2}(?:const|let)\s+[\w{[\], ]+=\s*use[A-Z]\w*\(/
const HOOK_BAR = /^ {2}use(?:Effect|LayoutEffect)\(/
const TIDLIG_RETURN = /^ {2}if\s*\(.*\)\s*return\b/

function tsxFiler(mappe: string): string[] {
  const ud: string[] = []
  for (const navn of readdirSync(mappe)) {
    const sti = join(mappe, navn)
    if (statSync(sti).isDirectory()) { ud.push(...tsxFiler(sti)); continue }
    if (navn.endsWith('.tsx') && !navn.includes('.test.')) ud.push(sti)
  }
  return ud
}

/** Linjenumre hvor et hook står efter en tidlig return i samme funktion. */
function hooksEfterReturn(kilde: string): number[] {
  const linjer = kilde.split('\n')
  const fund: number[] = []
  let sidsteReturn = -1
  linjer.forEach((l, i) => {
    // En ny funktion på top-niveau nulstiller — hver komponent har sit eget
    // hook-regnskab.
    if (/^(export )?(function|const)\s+[A-Z]/.test(l)) sidsteReturn = -1
    if (TIDLIG_RETURN.test(l)) sidsteReturn = i
    if (sidsteReturn >= 0 && (HOOK.test(l) || HOOK_BAR.test(l))) fund.push(i + 1)
  })
  return fund
}

describe('rules of hooks', () => {
  it('ingen hooks efter en betinget return', () => {
    const brud: string[] = []
    for (const fil of tsxFiler(ROD)) {
      const linjer = hooksEfterReturn(readFileSync(fil, 'utf-8'))
      if (linjer.length) brud.push(`${fil.replace(ROD, 'src')}:${linjer.join(',')}`)
    }
    expect(brud, 'hook efter betinget return — React #310').toEqual([])
  })

  it('fanger mønstret den blev skrevet til', () => {
    const dårlig = [
      'export function App() {',
      '  const { settings } = useSettings()',
      '  if (!settings) return null',
      '  const cfg = useMemo(() => ({}), [])',
      '  return <div />',
      '}',
    ].join('\n')
    expect(hooksEfterReturn(dårlig)).toEqual([4])
  })

  it('en return EFTER alle hooks er i orden', () => {
    const god = [
      'export function App() {',
      '  const { settings } = useSettings()',
      '  const cfg = useMemo(() => ({}), [])',
      '  if (!settings) return null',
      '  return <div />',
      '}',
    ].join('\n')
    expect(hooksEfterReturn(god)).toEqual([])
  })
})
