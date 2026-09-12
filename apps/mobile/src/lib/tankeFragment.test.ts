import { tankeFragment } from './tankeFragment'

it('viser den SIDSTE linje — det er dér han er nu', () => {
  // Begyndelsen er det man allerede har set rulle forbi.
  expect(tankeFragment('foerst dette\nsaa dette\nog nu dette')).toBe('og nu dette')
})

it('tomme linjer springes over frem for at give en tom etiket', () => {
  expect(tankeFragment('noget\n\n\n')).toBe('noget')
})

it('ingen tanke giver tom streng, ikke «undefined»', () => {
  expect(tankeFragment(undefined)).toBe('')
  expect(tankeFragment('   ')).toBe('')
})

it('lange linjer forkortes ved et MELLEMRUM', () => {
  // Et ord hugget midt over ligner en fejl, ikke en forkortelse.
  const lang = 'jeg undersøger om testen fejler fordi konfigurationen bindes på importtidspunktet'
  const ud = tankeFragment(lang, 40)
  expect(ud.endsWith('…')).toBe(true)
  expect(ud.length).toBeLessThanOrEqual(41)
  // ORDGRAENSE, ikke «ingen bogstav foer prikkerne»: teksten uden ellipsen
  // skal vaere et praefiks af originalen der slutter hvor der ER et mellemrum.
  // (Foerste udgave af denne test haevdede /\S…$/ og anklagede dermed det
  // rigtige svar — «fordi…» ER en ren ordgraense.)
  const uden = ud.slice(0, -1)
  expect(lang.startsWith(uden)).toBe(true)
  expect(lang[uden.length]).toBe(' ')
})

it('et enkelt meget langt ord hugges alligevel — ellers vokser linjen frit', () => {
  const ud = tankeFragment('a'.repeat(200), 30)
  expect(ud.length).toBeLessThanOrEqual(31)
})

it('en kort linje staar uroert', () => {
  expect(tankeFragment('kort nok')).toBe('kort nok')
})
