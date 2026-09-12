import { prikker } from './prikSekvens'

const synlige = (s: string) => s.replace(/ /g, '')

it('loeber ét, to, tre og forfra', () => {
  expect(synlige(prikker(0))).toBe('.')
  expect(synlige(prikker(1))).toBe('..')
  expect(synlige(prikker(2))).toBe('...')
  expect(synlige(prikker(3))).toBe('.')
})

it('bredden er FAST — etiketten maa ikke hoppe', () => {
  // Ved at fylde op med tynde mellemrum staar teksten efter prikkerne stille.
  expect(prikker(0)).toHaveLength(3)
  expect(prikker(1)).toHaveLength(3)
  expect(prikker(2)).toHaveLength(3)
})

it('negative trin braekker ikke', () => {
  // En taeller kan gaa i minus hvis nogen traekker fra i stedet for at laegge
  // til; resultatet skal stadig vaere en gyldig prik-sekvens.
  expect(synlige(prikker(-1))).toBe('...')
  expect(synlige(prikker(-3))).toBe('.')
})
