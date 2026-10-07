/** Lyden til notifikations-toasten (Bjørn 7/10-2026).
 *
 * HVORFOR SYNTHESE OG IKKE EN FIL. En lydfil skal pakkes med i build'et,
 * versioneres og hentes — og i Electron ligger den i app-bundlen. To toner
 * fra Web Audio koster ingen bytes, kan ikke fejle paa en manglende sti, og
 * kan stemmes pr. slags. Det er samme afvejning som ANSI-renderen tog.
 *
 * VALGET ER LOKALT. Det er en klient-praeference (hvordan MIN maskine skal
 * lyde), ikke en server-indstilling — og den hoerer derfor i localStorage
 * sammen med temaet, ikke i `notifikations-valg` paa serveren, hvor «kanal»
 * betyder noget andet (hvor posten skal LEVERES).
 *
 * Lyd maa ALDRIG vaelte visningen: alt her er pakket i try/catch, og en
 * browser der blokerer AudioContext foer foerste klik fejler tavst.
 */
const KEY = 'jarvis-desk:toast-lyd-v1'
export const TOAST_LYD_EVENT = 'jarvis-desk:toast-lyd'

export type Tone = 'fejl' | 'ok' | 'neutral'

/** To korte toner pr. slags. Fejl falder, de andre stiger. */
const TONER: Record<Tone, number[]> = {
  fejl: [420, 330],
  ok: [660, 880],
  neutral: [587, 784],
}

let ctx: AudioContext | null = null

export function toastLydTil(): boolean {
  try { return localStorage.getItem(KEY) !== 'fra' } catch { return true }
}

export function setToastLyd(til: boolean): void {
  try { localStorage.setItem(KEY, til ? 'til' : 'fra') } catch { /* privat storage */ }
  window.dispatchEvent(new Event(TOAST_LYD_EVENT))
}

export function spilToastKlang(tone: Tone = 'neutral'): void {
  if (!toastLydTil()) return
  try {
    const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!AC) return
    ctx = ctx ?? new AC()
    if (ctx.state === 'suspended') void ctx.resume()

    const nu = ctx.currentTime
    TONER[tone].forEach((frekvens, i) => {
      const osc = ctx!.createOscillator()
      const gain = ctx!.createGain()
      osc.type = 'sine'
      osc.frequency.value = frekvens
      const t0 = nu + i * 0.1
      gain.gain.setValueAtTime(0, t0)
      gain.gain.linearRampToValueAtTime(0.16, t0 + 0.015)
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.32)
      osc.connect(gain); gain.connect(ctx!.destination)
      osc.start(t0); osc.stop(t0 + 0.34)
    })
  } catch { /* lyd er en dyd, ikke et krav */ }
}
