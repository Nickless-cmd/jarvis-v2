/**
 * Vinduets plads — position, størrelse og maksimeret-tilstand — huskes.
 *
 * Bjørn 16/9-2026: «husk at appen skal huske position efter restart».
 *
 * Appen åbnede hver gang på 1280x800 midt på skærmen, uanset hvor man havde
 * lagt den. Med tre skærme betyder det at den lander et andet sted end man
 * forlod den, hver eneste gang.
 *
 * TRE TING DER IKKE ER TIL PYNT:
 *
 *  1. Der gemmes DEBOUNCED. `move` og `resize` fyrer for hver eneste pixel
 *     under et træk; et filskriv pr. pixel er hundredvis af skrivninger for
 *     én flytning.
 *
 *  2. Er vinduet maksimeret, gemmes den NORMALE størrelse (`getNormalBounds`)
 *     sammen med flaget. Ellers ville et gendan efter genstart give et vindue
 *     på skærmens fulde størrelse — «gendan» til noget der ikke var der før.
 *
 *  3. Pladsen efterprøves mod de skærme der ER tilsluttet. Tages en skærm væk
 *     — eller kobles maskinen til en dock med en anden opstilling — ville de
 *     gemte koordinater lægge vinduet uden for alt synligt, og så er appen
 *     væk uden at være lukket.
 */
import { app, BrowserWindow, screen } from 'electron'
import fs from 'fs'
import path from 'path'

export interface Vinduesplads {
  x?: number
  y?: number
  width: number
  height: number
  maximized?: boolean
}

export const STANDARD: Vinduesplads = { width: 1280, height: 800 }

function filsti(): string {
  return path.join(app.getPath('userData'), 'vinduesplads.json')
}

export function laesPlads(): Vinduesplads {
  try {
    const raa = JSON.parse(fs.readFileSync(filsti(), 'utf-8')) as Partial<Vinduesplads>
    const b = Number(raa.width), h = Number(raa.height)
    if (!Number.isFinite(b) || !Number.isFinite(h) || b < 200 || h < 200) return STANDARD
    return {
      width: Math.round(b),
      height: Math.round(h),
      ...(Number.isFinite(Number(raa.x)) ? { x: Math.round(Number(raa.x)) } : {}),
      ...(Number.isFinite(Number(raa.y)) ? { y: Math.round(Number(raa.y)) } : {}),
      maximized: !!raa.maximized,
    }
  } catch {
    // Ingen fil, eller en ødelagt en. En vinduesplads er ikke værd at
    // stoppe opstarten over.
    return STANDARD
  }
}

export function skrivPlads(p: Vinduesplads): void {
  try {
    fs.writeFileSync(filsti(), JSON.stringify(p, null, 2), { mode: 0o600 })
  } catch { /* se ovenfor */ }
}

/**
 * Ligger pladsen inden for en skærm der FINDES?
 *
 * Adskilt fra resten så den kan testes uden en kørende Electron: skærmene
 * gives ind som rektangler.
 */
export function erSynlig(
  p: Vinduesplads,
  skaerme: { x: number; y: number; width: number; height: number }[],
): boolean {
  if (p.x === undefined || p.y === undefined) return true   // uden position = centreret
  // Der kræves ikke fuld dækning — et vindue må gerne hænge ud over kanten.
  // Kravet er at et brugbart HJØRNE er synligt, så man kan få fat i det.
  const MARGEN = 80
  const BJAELKE = 30          // hoejden man griber vinduet i
  return skaerme.some((s) =>
    p.x! + MARGEN < s.x + s.width &&
    p.x! + p.width - MARGEN > s.x &&
    // Bjaelken skal ligge INDEN FOR skaermen lodret — baade at den ikke er
    // under bunden OG at den ikke er over toppen. Foerste udgave tjekkede kun
    // det foerste, saa et vindue paa y = -200 talte som synligt selv om
    // bjaelken laa 200 px over skaermkanten og ikke kunne gribes.
    p.y! + BJAELKE < s.y + s.height &&
    p.y! + BJAELKE > s.y)
}

/** Pladsen, efterprøvet mod de tilsluttede skærme. Duer den ikke, falder vi
 *  tilbage til størrelsen uden position — så centrerer Electron selv. */
export function brugbarPlads(): Vinduesplads {
  const p = laesPlads()
  try {
    const skaerme = screen.getAllDisplays().map((d) => d.workArea)
    if (!erSynlig(p, skaerme)) return { width: p.width, height: p.height, maximized: p.maximized }
  } catch { /* uden skaerm-info bruges pladsen som den er */ }
  return p
}

/** Hæft lytterne på vinduet. Returnerer en funktion der gemmer med det samme
 *  (til brug lige før appen lukker). */
export function husk(vindue: BrowserWindow): () => void {
  let timer: NodeJS.Timeout | null = null

  const gem = () => {
    if (vindue.isDestroyed()) return
    // getNormalBounds: den størrelse vinduet har UDEN maksimering. Se noten
    // i toppen — ellers bliver «gendan» til fuld skærm.
    const b = vindue.getNormalBounds()
    skrivPlads({
      x: b.x, y: b.y, width: b.width, height: b.height,
      maximized: vindue.isMaximized(),
    })
  }

  const senere = () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(gem, 400)
  }

  vindue.on('move', senere)
  vindue.on('resize', senere)
  vindue.on('maximize', senere)
  vindue.on('unmaximize', senere)
  // Lukkes vinduet, skal den sidste plads med — uden dette ville de sidste
  // 400 ms af en flytning gå tabt netop når man lukker appen.
  vindue.on('close', gem)
  return gem
}
