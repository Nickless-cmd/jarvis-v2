import { createContext } from 'react'
import type { DeferredToolRequest, DeferredToolUdfald } from './fladeHandling'

export type FladeDeferredTurn = {
  accountId: string
  conversationId: string
  sourceMessageId: string
  run: (request: DeferredToolRequest) => Promise<DeferredToolUdfald>
}

/** Default-null er code-mode-gaten: kun chat-visningen monterer provideren. */
export const FladeDeferredTurnContext = createContext<FladeDeferredTurn | null>(null)
