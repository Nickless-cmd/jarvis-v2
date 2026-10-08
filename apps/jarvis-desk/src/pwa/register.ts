/** Listen for a waiting build. It stays idle until the user chooses to reload. */
export function registerPwa(onWaiting: (worker: ServiceWorker) => void): () => void {
  if (!__WEB_BUILD__ || !('serviceWorker' in navigator)) return () => {}
  let live = true
  let registration: ServiceWorkerRegistration | undefined
  const waiting = () => {
    if (live && registration?.waiting && navigator.serviceWorker.controller) onWaiting(registration.waiting)
  }
  const onVisibility = () => { if (document.visibilityState === 'visible') void registration?.update().catch(() => {}) }
  void navigator.serviceWorker.register('/sw.js', { scope: '/' }).then((reg) => {
    if (!live) return
    registration = reg
    waiting()
    reg.addEventListener('updatefound', () => {
      const installing = reg.installing
      installing?.addEventListener('statechange', waiting)
    })
  }).catch(() => {})
  document.addEventListener('visibilitychange', onVisibility)
  return () => { live = false; document.removeEventListener('visibilitychange', onVisibility) }
}
