import { describe, it, expect } from 'vitest'
import { udgivetFil } from './raekkeKroppe'

describe('udgivetFil', () => {
  it('finder /files/-adressen og navnet', () => {
    expect(udgivetFil({ url: '/files/rapport.md', filename: 'rapport.md' })).toEqual({ url: '/files/rapport.md', filename: 'rapport.md' })
  })
  it('gør en absolut URL til stien', () => {
    expect(udgivetFil({ download_url: 'https://api.x/files/a%20b.txt' })?.url).toBe('/files/a%20b.txt')
  })
  it('afviser fremmede URL-er', () => {
    expect(udgivetFil({ url: 'https://evil.example/x.exe' })).toBeNull()
    expect(udgivetFil('ingen')).toBeNull()
  })
})
