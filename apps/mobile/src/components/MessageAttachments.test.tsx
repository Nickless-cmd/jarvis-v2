import { formatSize } from './MessageAttachments'

describe('formatSize', () => {
  it('viser bytes under 1 kB', () => {
    expect(formatSize(512)).toBe('512 B')
  })

  it('bruger dansk komma og skjuler tom decimal', () => {
    expect(formatSize(1536)).toBe('1,5 kB')
    expect(formatSize(2048)).toBe('2 kB')
  })

  it('gaar op i MB og GB', () => {
    expect(formatSize(5 * 1024 * 1024)).toBe('5 MB')
    expect(formatSize(3 * 1024 * 1024 * 1024)).toBe('3 GB')
  })
})
