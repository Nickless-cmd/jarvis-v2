import * as push from './push'

/**
 * «Jarvis arbejder»-notifikationen skal væk.
 *
 * Den blev vist hver gang man forlod appen midt i et svar: «Du kan lukke
 * skærmen. Runnet fortsætter på serveren.» Bjørn 28/9-2026: «den skal væk» —
 * med et skærmbillede hvor der lå to stablet.
 *
 * Den var `ongoing: true, autoCancel: false`, altså kunne den ikke swipes væk.
 * Derfor er det ikke nok at holde op med at vise den: rydningen skal blive,
 * ellers sidder en fra en tidligere udgave fast for evigt.
 */

it('der findes ingen afsender mere', () => {
  expect('showRunInProgressNotification' in push).toBe(false)
})

it('men rydningen er der stadig — en fastlåst skal kunne fjernes', () => {
  expect(typeof (push as Record<string, unknown>).clearRunInProgressNotification)
    .toBe('function')
})

/** Ordene må gerne stå i en kommentar — de skal bare ikke BÆRES af en
 *  notifikation. Testen kigger derfor på felterne, ikke på hele filen. */
it('ingen notifikation bærer teksten længere', () => {
  const kilde = require('node:fs').readFileSync(
    require('node:path').join(__dirname, 'push.ts'), 'utf-8') as string
  const felter = kilde
    .split('\n')
    .filter((l) => /^\s*(title|body):/.test(l))
    .join('\n')
  expect(felter).not.toContain('Du kan lukke skærmen')
  expect(felter).not.toContain('Jarvis arbejder')
  expect(felter).not.toContain('fortsætter på serveren')
})

/** Den var `ongoing`, så den kan ikke swipes væk. Bliver rydningen fjernet,
 *  sidder en fra en tidligere udgave fast for evigt. */
it('ChatScreen rydder den ved opstart, ikke kun ved retur', () => {
  const kilde = require('node:fs').readFileSync(
    require('node:path').join(__dirname, '..', 'screens', 'ChatScreen.tsx'),
    'utf-8') as string
  expect(kilde).toContain('useEffect(() => { void clearRunInProgressNotification() }, [])')
  expect(kilde).not.toContain('showRunInProgressNotification')
})
