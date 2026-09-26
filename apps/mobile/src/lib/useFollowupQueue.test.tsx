import { act, renderHook, waitFor } from '@testing-library/react-native'
import { useFollowupQueue } from './useFollowupQueue'

it('redigerer, flytter og fjerner individuelle follow-ups uden at sende under runnet', async () => {
  const send = jest.fn()
  const steer = jest.fn().mockResolvedValue(undefined)
  const h = await renderHook((props: { busy: boolean }) => useFollowupQueue({
    sessionId: 'a', online: true, busy: props.busy, send, steer,
  }), { initialProps: { busy: true } })
  await act(async () => {
    h.result.current.enqueue('første')
    h.result.current.enqueue('anden')
  })
  expect(h.result.current.items.map((i) => i.text)).toEqual(['første', 'anden'])
  const [first, second] = h.result.current.items
  await act(async () => {
    h.result.current.edit(second!.id, 'rettet')
    h.result.current.move(second!.id, -1)
  })
  expect(h.result.current.items.map((i) => i.text)).toEqual(['rettet', 'første'])
  await act(async () => { h.result.current.remove(first!.id) })
  expect(h.result.current.items.map((i) => i.text)).toEqual(['rettet'])
  expect(send).not.toHaveBeenCalled()
})

it('sender kun første besked efter afslutning og næste efter endnu et run', async () => {
  const send = jest.fn()
  const h = await renderHook((busy: boolean) => useFollowupQueue({
    sessionId: 'a', online: true, busy, send, steer: jest.fn(),
  }), { initialProps: true })
  await act(async () => {
    h.result.current.enqueue('første')
    h.result.current.enqueue('anden')
  })
  await h.rerender(false)
  await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  expect(send.mock.calls[0][0].text).toBe('første')
  expect(h.result.current.items.map((i) => i.text)).toEqual(['anden'])
  await h.rerender(true)
  await h.rerender(false)
  await waitFor(() => expect(send).toHaveBeenCalledTimes(2))
  expect(send.mock.calls[1][0].text).toBe('anden')
})

it('send nu styrer runnet og beholder beskeden hvis serveren afviser', async () => {
  const steer = jest.fn().mockRejectedValueOnce(new Error('Runnet er afsluttet')).mockResolvedValueOnce(undefined)
  const send = jest.fn()
  const h = await renderHook(() => useFollowupQueue({
    sessionId: 'a', online: true, busy: true, send, steer,
  }))
  await act(async () => { h.result.current.enqueue('skift retning') })
  const id = h.result.current.items[0]!.id
  await act(async () => { await h.result.current.sendNow(id) })
  expect(h.result.current.items).toHaveLength(1)
  expect(h.result.current.error).toBe('Runnet er afsluttet')
  await act(async () => { await h.result.current.sendNow(id) })
  expect(steer).toHaveBeenCalledTimes(2)
  expect(h.result.current.items).toHaveLength(0)
  expect(send).not.toHaveBeenCalled()
})

it('skjuler andre samtalers kø og sender aldrig deres beskeder i den aktive samtale', async () => {
  const send = jest.fn()
  const h = await renderHook((props: { sessionId: string; busy: boolean }) => useFollowupQueue({
    ...props, online: true, send, steer: jest.fn(),
  }), { initialProps: { sessionId: 'a', busy: true } })
  await act(async () => { h.result.current.enqueue('kun a') })
  await h.rerender({ sessionId: 'b', busy: false })
  expect(h.result.current.items).toHaveLength(0)
  expect(send).not.toHaveBeenCalled()
  await h.rerender({ sessionId: 'a', busy: false })
  await waitFor(() => expect(send).toHaveBeenCalledTimes(1))
  expect(send.mock.calls[0][0].sessionId).toBe('a')
})
