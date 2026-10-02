import { describe, expect, it } from 'vitest'
import { rendererCsp } from './rendererCsp'

describe('renderer CSP', () => {
  const connectOrigins = ['https://api.srvlab.dk', 'wss://api.srvlab.dk']

  it('allows Shiki WebAssembly without allowing arbitrary JavaScript eval in production', () => {
    const directives = rendererCsp({ development: false, connectOrigins })
    expect(directives).toContain("script-src 'self' 'wasm-unsafe-eval'")
    expect(directives.join('; ')).not.toContain("'unsafe-eval'")
    expect(directives).toContain("connect-src 'self' https://api.srvlab.dk wss://api.srvlab.dk")
  })

  it('keeps Vite development script and connection permissions', () => {
    const directives = rendererCsp({ development: true, connectOrigins })
    expect(directives).toContain("script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5174")
    expect(directives.join('; ')).toContain('ws://localhost:5174')
  })
})
