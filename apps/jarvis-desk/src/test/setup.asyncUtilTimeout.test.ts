/**
 * Vagt for den globale ventetid på `findBy*` og `waitFor`.
 *
 * 29/10-2026 faldt `ChatView.test.tsx > shows optimistic user msg` på CI med
 * «Unable to find an element with the text: hej» efter 1205 ms — samme test
 * svarede 355 ms lokalt og bestod 8/8 isoleret. Hele suiten tog 187 s på CI
 * mod 75 s her, så runneren er ~2,5× langsommere, og standardens 1000 ms er
 * for kort til at en grøn test ikke fældes af maskinens tempo.
 *
 * Testen læser den KØRENDE konfiguration, ikke kilden. Det er med vilje:
 * en test der greppede efter strengen `asyncUtilTimeout` i `setup.ts` ville
 * stadig være grøn hvis `configure()`-kaldet stod i en gren der aldrig blev
 * nået, eller hvis `setupFiles` blev fjernet fra vitest-config'en. Her måles
 * den værdi biblioteket faktisk bruger når testene kører.
 */
import { describe, expect, it } from 'vitest'
import { getConfig } from '@testing-library/dom'

describe('test-setup — ventetiden på findBy/waitFor', () => {
  it('er hævet over standardens 1000 ms, så CI-last ikke fælder en grøn test', () => {
    // Målt 29/10-2026: fejlen indtraf ved 1205 ms på CI. Grænsen skal have
    // luft over det tal, ellers gentager fejlen sig ved den mindste last.
    expect(getConfig().asyncUtilTimeout).toBeGreaterThanOrEqual(3000)
  })

  it('er ikke hævet så meget at en test der venter forgæves hænger i minutter', () => {
    // Et loft er lige så vigtigt som et gulv: `waitFor` på noget der aldrig
    // kommer skal fejle inden for overskuelig tid, ellers bliver en rød suite
    // ubrugelig som signal.
    expect(getConfig().asyncUtilTimeout).toBeLessThanOrEqual(10_000)
  })
})
