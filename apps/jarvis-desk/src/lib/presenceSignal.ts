// Delt interaktions-signal mellem ChatView (sætter ved send) og PresenceHost
// (læser ved næste presence-ping). Lille modul-flag — ingen context nødvendig.
let _interacted = true // app-åbning tæller som interaktion

export function markInteraction(): void {
  _interacted = true
}

export function consumeInteraction(): boolean {
  const v = _interacted
  _interacted = false
  return v
}
