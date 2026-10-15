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

  it('lukker widget-scripts op med en nonce uden at aabne unsafe-inline', () => {
    // Maalt 15/10-2026: en srcdoc-iframe ARVER foraelderens policy, saa uden
    // noncen koerte widget'ens inline-script slet ikke i den pakkede app —
    // mens det koerte fint paa web-fladen. Noncen er svaret; `'unsafe-inline'`
    // er det fristende svar der aabner HELE rendereren.
    const directives = rendererCsp({ development: false, connectOrigins, widgetNonce: 'aB3+/x==' })
    expect(directives).toContain("script-src 'self' 'wasm-unsafe-eval' 'nonce-aB3+/x=='")
    // Praecist script-src og ikke hele listen: prod-CSP'en HAR `'unsafe-inline'`
    // i `style-src` med vilje — en bred soegning ville fejle paa den og se ud
    // som om noncen aabnede noget den ikke goer.
    const scriptSrc = directives.find((d) => d.startsWith('script-src'))
    expect(scriptSrc).not.toContain("'unsafe-inline'")
  })

  it('udelader nonce-direktivet naar der ikke er nogen nonce', () => {
    // En tom `'nonce-'` er en syntaksfejl der dropper HELE script-src — og saa
    // ville selv Shiki doe. Direktivet skal staa urørt.
    for (const nonce of [undefined, '']) {
      const directives = rendererCsp({ development: false, connectOrigins, widgetNonce: nonce })
      expect(directives).toContain("script-src 'self' 'wasm-unsafe-eval'")
      expect(directives.join('; ')).not.toContain('nonce-')
    }
  })

  it('saetter ALDRIG nonce i dev-grenen, hvor unsafe-inline stadig skal virke', () => {
    // I dev er Vite og Reacts egne inline-scripts baaret af `'unsafe-inline'`.
    // En nonce i samme direktiv ophaever den regel — og dev ville doe.
    const directives = rendererCsp({
      development: true,
      connectOrigins,
      widgetNonce: 'aB3+/x==',
    })
    expect(directives).toContain("script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5174")
    expect(directives.join('; ')).not.toContain('nonce-')
  })

  it('keeps Vite development script and connection permissions', () => {
    const directives = rendererCsp({ development: true, connectOrigins })
    expect(directives).toContain("script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5174")
    expect(directives.join('; ')).toContain('ws://localhost:5174')
  })
})
