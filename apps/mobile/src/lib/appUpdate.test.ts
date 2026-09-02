import { compareVersion, checkForUpdate } from './appUpdate'

describe('compareVersion', () => {
  it('true når manifest er nyere', () => {
    expect(compareVersion(28, { version_code: 30 })).toBe(true)
  })
  it('false når manifest er samme', () => {
    expect(compareVersion(30, { version_code: 30 })).toBe(false)
  })
  it('false når manifest er ældre', () => {
    expect(compareVersion(31, { version_code: 30 })).toBe(false)
  })
  it('false når version_code mangler', () => {
    expect(compareVersion(28, {})).toBe(false)
  })
})

const cfg = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'tok' }

function mockFetch(status: number, body: unknown) {
  return jest.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })) as unknown as typeof fetch
}

describe('checkForUpdate', () => {
  afterEach(() => jest.restoreAllMocks())

  it('returnerer manifest når nyere', async () => {
    global.fetch = mockFetch(200, { version: '0.1.29', version_code: 30, notes: 'n', filename: 'a.apk' })
    const r = await checkForUpdate(cfg, 28)
    expect(r?.version_code).toBe(30)
  })

  it('returnerer null når samme version', async () => {
    global.fetch = mockFetch(200, { version: '0.1.29', version_code: 30, notes: 'n', filename: 'a.apk' })
    expect(await checkForUpdate(cfg, 30)).toBeNull()
  })

  it('returnerer null på tomt manifest', async () => {
    global.fetch = mockFetch(200, {})
    expect(await checkForUpdate(cfg, 28)).toBeNull()
  })

  it('returnerer null ved fetch-fejl', async () => {
    global.fetch = jest.fn(async () => { throw new Error('network') }) as unknown as typeof fetch
    expect(await checkForUpdate(cfg, 28)).toBeNull()
  })
})
