import { formatTid } from './InlineToolGroup'

// Klokken i Claude Desktops format (`BS`) — samme som desk.
it('sekunder, minutter, timer', () => {
  expect(formatTid(12)).toBe('12s')
  expect(formatTid(65)).toBe('1m 5s')
  expect(formatTid(3723)).toBe('1h 2m 3s')
})
