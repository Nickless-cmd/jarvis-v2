import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { optag, opdaterStatus, _nulstil, _sætAktiv, _buffer, _flushNu } from './streamCapture'

/**
 * Bjørn 8/9-2026: «lad os logge mine samtaler … den skal optage helt ude fra
 * klienten, ALT streaming, alt.»
 *
 * De tre egenskaber der gør optagelsen brugbar: den fanger ALT (også rammer
 * der ikke kan parses), den kan ikke vælte streamen, og den må ikke ændre det
 * den måler.
 */

function medBro(status: { active: boolean }, append = vi.fn().mockResolvedValue(true)) {
  ;(window as unknown as Record<string, unknown>).jarvisDesk = {
    capture: { status: vi.fn().mockResolvedValue(status), append },
  }
  return append
}

beforeEach(() => { _nulstil() })
afterEach(() => { delete (window as unknown as Record<string, unknown>).jarvisDesk })

describe('rå stream-optagelse', () => {
  it('optager rammer når optagelsen kører', async () => {
    const append = medBro({ active: true })
    await opdaterStatus()

    optag('message_start', '{"type":"message_start"}')
    optag('content_block_delta', '{"delta":"hej"}')
    await _flushNu()

    expect(append).toHaveBeenCalledTimes(1)
    const linjer = append.mock.calls[0]?.[0] as string[]
    expect(linjer).toHaveLength(2)
    const første = JSON.parse(linjer[0] as string)
    expect(første.e).toBe('message_start')
    expect(typeof første.t).toBe('number')
  })

  it('optager også rammer der IKKE er gyldig JSON', async () => {
    // Hooket sidder før parsingen med vilje: en ramme der ikke kan læses er
    // præcis den slags der kan forklare hvad han ser.
    const append = medBro({ active: true })
    await opdaterStatus()

    optag('content_block_delta', '{ ødelagt json')
    await _flushNu()

    const linjer = append.mock.calls[0]?.[0] as string[]
    expect(JSON.parse(linjer[0] as string).d).toBe('{ ødelagt json')
  })

  it('gemmer rækkefølgen — det er hele pointen', async () => {
    const append = medBro({ active: true })
    await opdaterStatus()

    optag('a', '1'); optag('b', '2'); optag('c', '3')
    await _flushNu()

    const linjer = (append.mock.calls[0]?.[0] as string[]).map((l) => JSON.parse(l).e)
    expect(linjer).toEqual(['a', 'b', 'c'])
  })

  it('skriver intet når optagelsen er slået fra', async () => {
    const append = medBro({ active: false })
    await opdaterStatus()

    optag('message_start', '{}')
    await _flushNu()

    expect(append).not.toHaveBeenCalled()
  })

  it('rører intet når broen ikke findes (browser/dev)', async () => {
    delete (window as unknown as Record<string, unknown>).jarvisDesk
    await opdaterStatus()
    expect(() => optag('x', 'y')).not.toThrow()
    expect(_buffer()).toHaveLength(0)
  })

  it('en fejlende skrivning vælter ikke streamen', async () => {
    const append = vi.fn().mockRejectedValue(new Error('disk fuld'))
    medBro({ active: true }, append)
    await opdaterStatus()

    optag('message_start', '{}')
    await expect(_flushNu()).resolves.toBeUndefined()
  })

  it('batcher frem for én skrivning pr. ramme', async () => {
    // Måleredskabet må ikke ændre det det måler: tusindvis af IPC-kald oven i
    // en stream vi mistænker for timing-problemer ville gøre optagelsen
    // værdiløs.
    const append = medBro({ active: true })
    await opdaterStatus()

    for (let i = 0; i < 40; i++) optag('content_block_delta', `{"i":${i}}`)
    await _flushNu()

    expect(append).toHaveBeenCalledTimes(1)
    expect((append.mock.calls[0]?.[0] as string[]).length).toBe(40)
  })

  it('optager ikke før status er kendt', () => {
    // aktiv === null: vi taber højst én ramme ved appstart frem for at gøre
    // hver eneste ramme til et await.
    medBro({ active: true })
    _sætAktiv(null)
    optag('message_start', '{}')
    expect(_buffer()).toHaveLength(0)
  })
})
