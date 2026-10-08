/**
 * Broen må aldrig ende stoppet uden en efterfølger — og aldrig i tavshed.
 *
 * ## Målingen (8/10-2026)
 *
 * Bjørn sad ikke ved maskinen og skulle bruge workstation-broen. Den havde
 * været død i ni timer. `~/.config/jarvisx/bridge.log` fortalte hele historien
 * på tre linjer:
 *
 *     03:23:21  ws close code=1012            ← serveren genstartede
 *     03:23:28  ws open — sending register    ← broen var tilbage på 7 sek
 *     03:58:40  ws close code=1000 reason=client_stop
 *
 * Og så ikke mere. Reconnect-logikken var uskyldig; den havde lige bevist sig
 * selv. Det var `bootstrapBridge` der kaldte `activeBridge.stop()` under
 * app-opdateringen kl. 05:58 og aldrig nåede til `start()`.
 *
 * `stop()` sætter `stopped = true`, og `scheduleReconnect()` returnerer straks
 * på det flag. Et hul mellem de to linjer er derfor ikke et blip — det er
 * permanent, indtil nogen genstarter appen i hånden. Og den eneste besked om
 * det gik til `console.warn`, hvis output ingen gemmer.
 *
 * Testene her læser main.ts som kilde. Det er med vilje: det der skal pinnes
 * er en EGENSKAB ved rækkefølgen i en funktion der kræver en kørende
 * Electron-app for at kalde, og en kilde-vagt fanger præcis den regression
 * der skete — at `stop()` kan stå uden garanteret efterfølger.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const kilde = readFileSync(join(__dirname, 'main.ts'), 'utf8')

/** Kroppen af `bootstrapBridge`, fra signatur til den afsluttende `}` i kolonne 0. */
function bootstrapKrop(): string {
  const start = kilde.indexOf('async function bootstrapBridge()')
  expect(start).toBeGreaterThan(-1)
  const slut = kilde.indexOf('\n}\n', start)
  expect(slut).toBeGreaterThan(start)
  return kilde.slice(start, slut)
}

/**
 * Den YDRE catch-blok — funktionens fejlgren.
 *
 * Foerste udgave brugte `indexOf('} catch')`, som rammer det INDRE
 * `try { activeBridge.stop() } catch { /* noop *\/ }` laengere oppe. «Fejlgrenen»
 * blev derfor hele funktionens hale, og en mutation der fjernede `broLog` fra
 * den rigtige catch slap igennem, fordi ordet stadig stod i en linje der
 * hoerte til den normale vej. Vagten maalte sig selv.
 *
 * Den ydre catch er den SIDSTE i funktionen og staar i kolonne 2.
 */
function fejlgren(): string {
  const krop = bootstrapKrop()
  const i = krop.lastIndexOf('\n  } catch')
  expect(i, 'fandt ikke den ydre catch-blok i bootstrapBridge').toBeGreaterThan(-1)
  return krop.slice(i)
}

describe('bootstrapBridge efterlader aldrig en stoppet bro', () => {
  it('kalder start() efter hvert stop() i samme funktion', () => {
    const krop = bootstrapKrop()
    const stopIdx = krop.indexOf('.stop()')
    const startIdx = krop.indexOf('.start()')
    expect(stopIdx).toBeGreaterThan(-1)
    expect(startIdx).toBeGreaterThan(stopIdx)
  })

  it('skriver bootstrap-fejl til bridge.log, ikke kun til konsollen', () => {
    const gren = fejlgren()
    expect(gren).not.toContain('bootstrap: ny bro startet')  // vi ser paa FEJLvejen
    expect(
      gren.includes('broLog'),
      'bootstrap-fejl må ikke kun gå til console.warn — appens stdout gemmes ' +
      'ingen steder, og det er grunden til at ni timers brotab ikke efterlod et spor',
    ).toBe(true)
  })

  it('planlægger et nyt forsøg når bootstrap fejler', () => {
    expect(
      fejlgren(),
      'uden et genforsøg er en forbigående fejl permanent: stop() har sat ' +
      'stopped=true, så broens egen reconnect er slået fra',
    ).toContain('planlaegBootstrapGenforsoeg')
  })

  it('har kun ÉN genforsøgs-timer ad gangen', () => {
    // config:set kan fyre flere gange i træk; uden vagten bliver N fejlede
    // bootstraps til N parallelle timere der hver kalder bootstrapBridge.
    expect(kilde).toContain('let genforsoegPlanlagt = false')
    const fn = kilde.slice(kilde.indexOf('function planlaegBootstrapGenforsoeg'))
    expect(fn.slice(0, 200)).toContain('if (genforsoegPlanlagt) return')
  })

  it('genforsøget venter — det hamrer ikke', () => {
    const m = kilde.match(/const BOOTSTRAP_GENFORSOEG_MS = ([\d_]+)/)
    expect(m).toBeTruthy()
    const ms = Number(m![1].replace(/_/g, ''))
    expect(ms).toBeGreaterThanOrEqual(5_000)
    expect(ms).toBeLessThanOrEqual(60_000)
  })
})

describe('broLog er den vej fejl skal ud', () => {
  it('eksporteres fra bridge.ts og skriver til bridge.log', () => {
    const bro = readFileSync(join(__dirname, 'bridge.ts'), 'utf8')
    expect(bro).toContain('export function broLog')
    const fn = bro.slice(bro.indexOf('export function broLog'))
    expect(fn.slice(0, 120)).toContain('fileLog')
  })

  it('bridge.log er stedet broen selv skriver til', () => {
    const bro = readFileSync(join(__dirname, 'bridge.ts'), 'utf8')
    expect(bro).toContain("'.config', 'jarvisx', 'bridge.log'")
  })
})
