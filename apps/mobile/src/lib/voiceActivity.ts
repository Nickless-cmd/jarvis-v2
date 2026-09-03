/**
 * Hvornår er en ytring slut, og hvornår bliver han afbrudt?
 *
 * Begge dele afgøres af ét tal: mikrofonens niveau i dB. Regnestykket ligger
 * her — uden timere, uden optager, uden React — så det kan afprøves med tal i
 * stedet for med en stemme i et rum.
 *
 * Niveauet SKAL hentes med `recorder.getStatus()`. Status-tilbagekaldet på
 * `useAudioRecorder` bærer ikke metering; det fyrer først når optagelsen
 * SLUTTER. Hænderfri var bygget på det tilbagekald, og derfor stoppede den
 * aldrig af sig selv: hverken stilheds-grænsen eller maks-længden lå et sted
 * der nogensinde blev kaldt.
 */

/** Måleren kommer i dB (-160..0). Tale ligger typisk mellem -45 og -10, så det
 *  er DET spænd der skal fylde skalaen — ikke hele registret, hvor almindelig
 *  tale ville se ud som næsten ingenting. */
export function levelFromDb(db: number): number {
  return Math.max(0, Math.min(1, (db + 48) / 38))
}

export interface SpeechWatch {
  /** Har der overhovedet været tale endnu? */
  sawSpeech: boolean
  /** Tidspunkt hvor stilheden begyndte. null = ikke stille.
   *  Sentinel'en er null og ikke 0, fordi 0 også er et gyldigt tidspunkt — en
   *  test der begyndte ved tiden 0 opførte sig som om intet var begyndt. */
  quietSince: number | null
}

export const freshWatch = (): SpeechWatch => ({ sawSpeech: false, quietSince: null })

export interface UtteranceOpts {
  /** Over dette regnes lyden som tale. */
  speechDb: number
  /** Så lang en pause afslutter ytringen. */
  silenceMs: number
}

/**
 * Er ytringen slut? Kræver at der HAR været tale først — ellers ville en
 * tavshed inden man overhovedet er begyndt at tale afslutte turen med det
 * samme, og man ville aldrig nå at sige noget.
 */
export function utteranceStep(
  w: SpeechWatch, db: number, now: number, o: UtteranceOpts,
): { watch: SpeechWatch; ended: boolean } {
  if (db > o.speechDb) return { watch: { sawSpeech: true, quietSince: null }, ended: false }
  if (!w.sawSpeech) return { watch: w, ended: false }
  const since = w.quietSince ?? now
  return { watch: { sawSpeech: true, quietSince: since }, ended: now - since >= o.silenceMs }
}

export interface LoudWatch {
  /** Tidspunkt hvor den vedvarende lyd begyndte. null = ikke i gang. */
  loudSince: number | null
}

export const freshLoud = (): LoudWatch => ({ loudSince: null })

export interface BargeOpts {
  /** Skal ligge HØJERE end tale-grænsen: mikrofonen hører også Jarvis' egen
   *  stemme fra højttaleren, og et enkelt smæld må ikke afbryde ham. */
  bargeDb: number
  /** Hvor længe der skal tales i træk. Et host eller en dør er kortere. */
  holdMs: number
}

/** Bliver han talt hen over? Kræver vedvarende lyd, ikke et enkelt udbrud. */
export function bargeStep(
  w: LoudWatch, db: number, now: number, o: BargeOpts,
): { watch: LoudWatch; hit: boolean } {
  if (db < o.bargeDb) return { watch: { loudSince: null }, hit: false }
  const since = w.loudSince ?? now
  return { watch: { loudSince: since }, hit: now - since >= o.holdMs }
}
