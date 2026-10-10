import { describe, expect, it } from 'vitest'

import { BridgeOutputLimiter } from './bridgeOutputBackpressure'

describe('BridgeOutputLimiter', () => {
  it('drops live deltas while websocket buffering is high and marks recovery', () => {
    const limiter = new BridgeOutputLimiter(1024)
    expect(limiter.next({ stream: 'stdout', seq: 1, chunk: 'lost' }, 2048)).toBeNull()
    expect(limiter.next({ stream: 'stdout', seq: 2, chunk: 'kept' }, 0)).toEqual({
      stream: 'stdout', seq: 2, chunk: 'kept', truncated: true,
    })
    expect(limiter.next({ stream: 'stdout', seq: 3, chunk: 'next' }, 0)).toEqual({
      stream: 'stdout', seq: 3, chunk: 'next',
    })
  })
})
