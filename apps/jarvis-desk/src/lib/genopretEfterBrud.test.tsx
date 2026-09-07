import { expect, it, vi } from 'vitest'
import { act, render } from '@testing-library/react'

import { useGenopretEfterBrud } from './genopretEfterBrud'

/** Genopretning efter et brud (Bjørn 7/9-2026).
 *
 *  Sporet hele vejen: serveren gennemfører turen og PERSISTERER svaret — kun
 *  leveringen fejler. Beskeden lå i basen og API'et returnerede den; skærmen
 *  fik den aldrig. `autoReconnect: false` er korrekt (duplikat-værn fra 2/9),
 *  men der manglede en LÆSE-vej tilbage.
 *
 *  Testen importerer den RIGTIGE hook. Første udgave kopierede den herind, og
 *  så beviste testen kun min egen kopi — samme fælde som jeg har påpeget to
 *  gange i dag. Derfor ligger hooken i sit eget modul.
 */
function Prøve({ status, sessionId, refresh }: {
  status: string; sessionId: string | null; refresh: () => Promise<void>
}) {
  useGenopretEfterBrud(status, sessionId, refresh)
  return null
}

it('henter svaret hjem når strømmen brister', async () => {
  const refresh = vi.fn().mockResolvedValue(undefined)
  await act(async () => { render(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />) })
  expect(refresh).toHaveBeenCalledTimes(1)
})

it('griber også når turen hænger', async () => {
  const refresh = vi.fn().mockResolvedValue(undefined)
  await act(async () => { render(<Prøve status="hung" sessionId="s1" refresh={refresh} />) })
  expect(refresh).toHaveBeenCalled()
})

it('rører intet mens strømmen kører', async () => {
  const refresh = vi.fn().mockResolvedValue(undefined)
  await act(async () => { render(<Prøve status="working" sessionId="s1" refresh={refresh} />) })
  expect(refresh).not.toHaveBeenCalled()
})

it('prøver igen når serveren stadig er nede', async () => {
  vi.useFakeTimers()
  const refresh = vi.fn()
    .mockRejectedValueOnce(new Error('nede'))
    .mockResolvedValueOnce(undefined)
  render(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(refresh).toHaveBeenCalledTimes(2)
  vi.useRealTimers()
})

it('giver op efter tre forsøg i stedet for at hamre', async () => {
  vi.useFakeTimers()
  const refresh = vi.fn().mockRejectedValue(new Error('nede'))
  render(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />)
  await act(async () => { await vi.advanceTimersByTimeAsync(20000) })
  expect(refresh).toHaveBeenCalledTimes(3)
  vi.useRealTimers()
})

it('henter kun ÉN gang pr. brud — ikke ved hver gentegning', async () => {
  const refresh = vi.fn().mockResolvedValue(undefined)
  const r = render(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />)
  await act(async () => { r.rerender(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />) })
  expect(refresh).toHaveBeenCalledTimes(1)
})

it('et NYT brud efter en normal tur griber igen', async () => {
  const refresh = vi.fn().mockResolvedValue(undefined)
  const r = render(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />)
  await act(async () => { r.rerender(<Prøve status="idle" sessionId="s1" refresh={refresh} />) })
  await act(async () => { r.rerender(<Prøve status="interrupted" sessionId="s1" refresh={refresh} />) })
  expect(refresh).toHaveBeenCalledTimes(2)
})
