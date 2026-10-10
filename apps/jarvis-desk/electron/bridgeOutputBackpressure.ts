export interface BridgeOutputDelta {
  stream: 'stdout' | 'stderr'
  seq: number
  chunk: string
  truncated?: boolean
}

export class BridgeOutputLimiter {
  private dropped = false

  constructor(private readonly maxBufferedBytes = 256 * 1024) {}

  next(delta: BridgeOutputDelta, bufferedBytes: number): BridgeOutputDelta | null {
    if (bufferedBytes > this.maxBufferedBytes) {
      this.dropped = true
      return null
    }
    if (!this.dropped) return delta
    this.dropped = false
    return { ...delta, truncated: true }
  }
}
