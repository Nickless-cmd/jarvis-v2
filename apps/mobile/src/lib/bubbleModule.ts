import { NativeModules } from 'react-native'

interface BubbleNative {
  isSupported(): Promise<boolean>
  floatCurrentChat(sessionId: string, title: string): void
  showConversationBubble(sessionId: string, title: string, body: string): void
  setPersistent(enabled: boolean, sessionId: string, title: string): void
}

const native: BubbleNative | undefined = NativeModules.BubbleModule

/** Tynd, sikker wrapper. Hvis det native modul mangler (iOS/gammel build/jest)
 *  bliver alt no-op og isSupported() → false. */
export const bubble = {
  async isSupported(): Promise<boolean> {
    if (!native) return false
    try {
      return await native.isSupported()
    } catch {
      return false
    }
  },
  floatCurrentChat(sessionId: string, title: string): void {
    try {
      native?.floatCurrentChat(sessionId, title)
    } catch {
      /* no-op */
    }
  },
  showConversationBubble(sessionId: string, title: string, body: string): void {
    try {
      native?.showConversationBubble(sessionId, title, body)
    } catch {
      /* no-op */
    }
  },
  setPersistent(enabled: boolean, sessionId: string, title: string): void {
    try {
      native?.setPersistent(enabled, sessionId, title)
    } catch {
      /* no-op */
    }
  },
}
