/**
 * Hvor skærm-listen kommer fra. Se skaerme.ts for hvorfor den findes.
 *
 * Rækkefølgen er med vilje: X selv først på Linux. `xrandr --listmonitors`
 * svarer med de rigtige Xinerama-heads, hvor Chromium kan vælge at se hele det
 * virtuelle skrivebord som ÉT display. Melder X kun én skærm, er Electron lige
 * så god — så vi tager X når den giver mere, og Electron ellers.
 *
 * Denne fil rører electron og starter xrandr, så den er IKKE ren og har ingen
 * tests. Al logik der kan testes ligger i skaerme.ts.
 */
import { execFileSync } from 'node:child_process'
import { platform } from 'node:os'
import { screen } from 'electron'
import { parseXrandrMonitors, type SkærmKilde } from './skaerme'

/** Kort frist: en hængende xrandr må ikke forsinke appens opstart. */
const XRANDR_TIMEOUT_MS = 2000

function laesFraXrandr(): SkærmKilde[] | null {
  try {
    const ud = execFileSync('xrandr', ['--listmonitors'], {
      encoding: 'utf8',
      timeout: XRANDR_TIMEOUT_MS,
    })
    return parseXrandrMonitors(ud)
  } catch {
    // Ingen xrandr, ingen DISPLAY, Wayland-session — ikke en fejl, bare en
    // anden vej til svaret. Electron kan svare på alle platforme.
    return null
  }
}

function laesFraElectron(): SkærmKilde[] {
  const primaer = screen.getPrimaryDisplay()
  return screen.getAllDisplays().map((d) => ({
    id: d.id,
    navn: d.label || `display-${d.id}`,
    primaer: d.id === primaer.id,
    x: d.bounds.x,
    y: d.bounds.y,
    width: d.bounds.width,
    height: d.bounds.height,
  }))
}

/**
 * Skærmene som værten ser dem.
 *
 * Læses ved behov frem for at caches: en skærm kan tændes, slukkes eller skifte
 * opløsning, og et gammelt svar ville få halo'en til at tegne ved siden af
 * markøren. Kaldet koster ét proces-start på Linux og intet på de andre.
 */
export function laesSkaerme(): SkærmKilde[] {
  if (platform() === 'linux') {
    const fraX = laesFraXrandr()
    if (fraX && fraX.length > 1) return fraX
  }
  return laesFraElectron()
}
