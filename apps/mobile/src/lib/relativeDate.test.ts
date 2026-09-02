import { formatRelativeDate } from './relativeDate'

const now = new Date('2026-06-18T15:00:00')

it('i dag / i går', () => {
  expect(formatRelativeDate('2026-06-18T09:00:00', now)).toBe('i dag')
  expect(formatRelativeDate('2026-06-17T23:00:00', now)).toBe('i går')
})

it('N dage inden for en uge', () => {
  expect(formatRelativeDate('2026-06-15T10:00:00', now)).toBe('3 dage')
})

it('dato for ældre', () => {
  expect(formatRelativeDate('2026-06-02T10:00:00', now)).toBe('2. jun')
})

it('tom/ugyldig → tom streng', () => {
  expect(formatRelativeDate(undefined, now)).toBe('')
  expect(formatRelativeDate('not-a-date', now)).toBe('')
})
