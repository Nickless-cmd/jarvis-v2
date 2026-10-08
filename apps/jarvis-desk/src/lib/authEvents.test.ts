import { describe, expect, it } from 'vitest'
import { onUnauthorized, reportUnauthorized } from './authEvents'

describe('unauthorized signal', () => {
  it('notifies an active subscriber and stops after unsubscribe', () => {
    let count = 0
    const stop = onUnauthorized(() => { count += 1 })
    reportUnauthorized()
    expect(count).toBe(1)
    stop()
    reportUnauthorized()
    expect(count).toBe(1)
  })
})
