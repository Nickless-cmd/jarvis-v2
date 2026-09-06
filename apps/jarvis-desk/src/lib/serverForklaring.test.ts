import { describe, expect, it } from 'vitest'
import { serverForklaring } from './api'

/** Serveren forklarer — brugeren skal se sætningen, ikke tallet eller JSON'en. */
function svar(status: number, body: string): Response {
  return { status, text: async () => body } as unknown as Response
}

describe('serverForklaring', () => {
  it('trækker detail ud i stedet for at vise rå JSON', async () => {
    // Set live: en godkendelse afvist som «stale» nåede brugeren som HTTP 409.
    const r = svar(409, '{"detail":"Capability approval request is stale and must be recreated"}')
    expect(await serverForklaring(r)).toBe(
      'Capability approval request is stale and must be recreated',
    )
  })

  it('tager også error-feltet', async () => {
    expect(await serverForklaring(svar(400, '{"error":"url is required"}'))).toBe('url is required')
  })

  it('tager første besked i en validerings-liste', async () => {
    const r = svar(422, '{"detail":[{"msg":"field required"}]}')
    expect(await serverForklaring(r)).toBe('field required')
  })

  it('viser rå tekst når svaret ikke er JSON', async () => {
    expect(await serverForklaring(svar(502, 'Bad Gateway'))).toContain('Bad Gateway')
  })

  it('falder tilbage til koden ved tom krop', async () => {
    expect(await serverForklaring(svar(500, ''))).toBe('HTTP 500')
  })

  it('kaster aldrig — også når kroppen ikke kan læses', async () => {
    const r = { status: 503, text: async () => { throw new Error('nede') } } as unknown as Response
    expect(await serverForklaring(r)).toBe('HTTP 503')
  })
})
