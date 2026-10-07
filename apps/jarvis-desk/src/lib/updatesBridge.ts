export interface UpdatesBridge {
  onAvailable: (cb: (i: { version?: string }) => void) => () => void
  onReady: (cb: (i: { version?: string }) => void) => () => void
  download: () => Promise<void>
  install: () => Promise<void>
  installNow: () => Promise<void>
}

export function updatesBridge(): UpdatesBridge | undefined {
  return (window as unknown as { jarvisDesk?: { updates?: UpdatesBridge } }).jarvisDesk?.updates
}
