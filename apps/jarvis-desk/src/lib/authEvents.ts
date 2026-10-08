const listeners = new Set<() => void>()

export function onUnauthorized(listener: () => void): () => void {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function reportUnauthorized(): void {
  for (const listener of listeners) listener()
}
