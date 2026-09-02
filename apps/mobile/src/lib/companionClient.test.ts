import { describePresence, relativeAge } from './companionClient'

describe('describePresence', () => {
  it('arbejder slaar alt andet', () => {
    expect(describePresence({ state: 'working', last_beat_ago_s: 9000 })).toBe('arbejder')
  })

  it('vaagen viser hvornaar hjertet sidst slog', () => {
    expect(describePresence({ state: 'awake', last_beat_ago_s: 300 }))
      .toBe('vågen · for 5 min siden')
  })

  it('stille naar slaget er gammelt', () => {
    expect(describePresence({ state: 'quiet', last_beat_ago_s: 7200 }))
      .toBe('stille · for 2 t siden')
  })

  // Indikatoren maa ALDRIG lyve. Kan vi ikke se ham, siger vi det.
  it('unknown viser grunden i stedet for at gaette', () => {
    expect(describePresence({ state: 'unknown', reason: 'kunne ikke nå Jarvis' }))
      .toBe('kunne ikke nå Jarvis')
  })
})

describe('relativeAge', () => {
  it('under halvandet minut er «lige nu»', () => {
    expect(relativeAge(45)).toBe('lige nu')
  })

  it('minutter, timer og dage', () => {
    expect(relativeAge(600)).toBe('for 10 min siden')
    expect(relativeAge(3 * 3600)).toBe('for 3 t siden')
    expect(relativeAge(48 * 3600)).toBe('for 2 dage siden')
    expect(relativeAge(24 * 3600)).toBe('for 1 dag siden')
  })
})
