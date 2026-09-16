import { describe, it, expect } from 'vitest'
import { erSynlig, STANDARD, type Vinduesplads } from './vinduesplads'

const skaerm = (x: number, y: number, width = 1920, height = 1080) => ({ x, y, width, height })
// Hans faktiske opstilling, maalt: tre skaerme side om side.
const TRE = [skaerm(0, 0), skaerm(1920, 0), skaerm(3840, 0)]

describe('vinduespladsen efterproeves mod de skaerme der FINDES', () => {
  it('en plads midt paa hovedskaermen er synlig', () => {
    expect(erSynlig({ x: 300, y: 200, width: 1280, height: 800 }, TRE)).toBe(true)
  })

  it('en plads paa den TREDJE skaerm er synlig', () => {
    expect(erSynlig({ x: 4000, y: 100, width: 1280, height: 800 }, TRE)).toBe(true)
  })

  it('samme plads er IKKE synlig naar skaermen er koblet fra', () => {
    // Det er hele pointen: uden dette ville appen aabne uden for alt synligt
    // og vaere «vaek» uden at vaere lukket.
    expect(erSynlig({ x: 4000, y: 100, width: 1280, height: 800 }, [skaerm(0, 0)])).toBe(false)
  })

  it('et vindue der hAENGER UD over kanten er stadig synligt', () => {
    // Der kraeves ikke fuld daekning — man skal bare kunne faa fat i det.
    expect(erSynlig({ x: 1700, y: 100, width: 1280, height: 800 }, [skaerm(0, 0)])).toBe(true)
  })

  it('et vindue hvis titelbjaelke ligger OVER skaermen kan ikke gribes', () => {
    expect(erSynlig({ x: 300, y: -200, width: 1280, height: 800 }, [skaerm(0, 0)])).toBe(false)
  })

  it('en plads UDEN position er altid i orden — Electron centrerer selv', () => {
    expect(erSynlig({ width: 1280, height: 800 }, [])).toBe(true)
  })

  it('standarden har en stoerrelse men ingen position', () => {
    const s: Vinduesplads = STANDARD
    expect(s.width).toBeGreaterThan(0)
    expect(s.x).toBeUndefined()
  })
})
