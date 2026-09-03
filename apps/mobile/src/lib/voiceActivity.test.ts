import { bargeStep, freshLoud, freshWatch, levelFromDb, utteranceStep } from './voiceActivity'

const O = { speechDb: -35, silenceMs: 1300 }

describe('utteranceStep', () => {
  // Uden dette krav ville tavsheden FØR man begynder at tale afslutte turen
  // med det samme, og man ville aldrig nå at sige noget.
  it('afslutter ikke før der har været tale', () => {
    let w = freshWatch()
    for (let t = 0; t < 10000; t += 120) {
      const r = utteranceStep(w, -60, t, O)
      w = r.watch
      expect(r.ended).toBe(false)
    }
  })

  it('afslutter efter tale fulgt af stilhed længe nok', () => {
    let w = freshWatch()
    w = utteranceStep(w, -20, 0, O).watch          // taler
    expect(utteranceStep(w, -60, 200, O).ended).toBe(false)
    w = utteranceStep(w, -60, 200, O).watch        // stilheden begynder
    expect(utteranceStep(w, -60, 1000, O).ended).toBe(false)
    expect(utteranceStep(w, -60, 1600, O).ended).toBe(true)
  })

  // En pause midt i en sætning må ikke sende halvdelen afsted.
  it('nulstiller stilheden når man taler videre', () => {
    let w = freshWatch()
    w = utteranceStep(w, -20, 0, O).watch
    w = utteranceStep(w, -60, 200, O).watch
    w = utteranceStep(w, -18, 900, O).watch        // taler igen
    expect(utteranceStep(w, -60, 1700, O).ended).toBe(false)
    expect(w.quietSince).toBeNull()
  })
})

describe('bargeStep', () => {
  const B = { bargeDb: -22, holdMs: 400 }

  // Mikrofonen hører også Jarvis' egen stemme fra højttaleren. Et enkelt
  // udbrud må ikke afbryde ham — det skal være vedvarende tale.
  it('afbryder ikke på et enkelt smæld', () => {
    let w = freshLoud()
    w = bargeStep(w, -10, 0, B).watch
    const r = bargeStep(w, -50, 150, B)
    expect(r.hit).toBe(false)
    expect(r.watch.loudSince).toBeNull()
  })

  // At tiden begynder ved 0 er ikke et kunstigt tilfælde — det er dét der
  // afslørede at «0» blev brugt både som tidspunkt og som «ikke i gang».
  it('afbryder når der tales vedvarende', () => {
    let w = freshLoud()
    w = bargeStep(w, -10, 0, B).watch
    expect(bargeStep(w, -12, 300, B).hit).toBe(false)
    expect(bargeStep(w, -12, 450, B).hit).toBe(true)
  })

  it('rører sig ikke ved almindelig baggrundslyd', () => {
    let w = freshLoud()
    for (let t = 0; t < 5000; t += 120) {
      const r = bargeStep(w, -34, t, B)
      w = r.watch
      expect(r.hit).toBe(false)
    }
  })
})

describe('levelFromDb', () => {
  it('lader almindelig tale fylde det meste af skalaen', () => {
    expect(levelFromDb(-160)).toBe(0)
    expect(levelFromDb(-48)).toBe(0)
    expect(levelFromDb(-30)).toBeGreaterThan(0.4)
    expect(levelFromDb(-10)).toBe(1)
  })
})
