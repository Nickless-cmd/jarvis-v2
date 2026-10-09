/** Listen for a waiting build. It stays idle until the user chooses to reload. */
export function registerPwa(onWaiting: (worker: ServiceWorker) => void): () => void {
  if (!__WEB_BUILD__ || !('serviceWorker' in navigator)) return () => {}
  let live = true
  let registration: ServiceWorkerRegistration | undefined
  // `registration.waiting` er KUN sat ved en ÆGTE opdatering: ved første
  // installation går workeren direkte til `activated` uden at vente. Det
  // tidligere krav om `navigator.serviceWorker.controller` betød derfor at
  // knappen ALDRIG blev vist på en frisk load — `controller` er null indtil en
  // worker har taget over — og klienten kørte videre på det gamle build i det
  // uendelige. Målt 9/10-2026: railen blev ved med at vise den gamle CSS selvom
  // serveren sendte den nye (side-885a39ab9e / side-1038357920).
  const waiting = () => {
    if (live && registration?.waiting) onWaiting(registration.waiting)
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
