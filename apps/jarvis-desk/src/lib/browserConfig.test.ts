import { beforeEach, describe, expect, it } from 'vitest'
import { clearBrowserConfig, readBrowserConfig, writeBrowserConfig } from './browserConfig'

const base = new URL('/', window.location.origin).toString()

describe('browser config', () => {
  beforeEach(() => localStorage.clear())

  it('starts unauthenticated on the current origin', () => {
    expect(readBrowserConfig()).toEqual({ apiBaseUrl: base, authToken: null })
  })

  it('survives reload and clears on logout', () => {
    writeBrowserConfig({ apiBaseUrl: base, authToken: 'test-token' })
    expect(readBrowserConfig()).toEqual({ apiBaseUrl: base, authToken: 'test-token' })
    clearBrowserConfig()
    expect(readBrowserConfig().authToken).toBeNull()
  })

  it('ignores malformed or foreign-origin credentials', () => {
    localStorage.setItem('jarvis:web-auth', '{broken')
    expect(readBrowserConfig().authToken).toBeNull()
    localStorage.setItem('jarvis:web-auth', JSON.stringify({ origin: 'https://other.example', authToken: 'test-token' }))
    expect(readBrowserConfig().authToken).toBeNull()
  })

  it('refuses to store credentials for another server', () => {
    writeBrowserConfig({ apiBaseUrl: 'https://other.example/', authToken: 'test-token' })
    expect(readBrowserConfig().authToken).toBeNull()
  })
})
