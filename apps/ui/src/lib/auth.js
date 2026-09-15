// Token-laget for web-UI'en.
//
// Indtil 15/9-2026 sendte denne UI INGEN legitimation. Hvert kald fik 401, og
// skallen blev staaende paa «Loading unified shell…» for evigt, fordi App.jsx
// returnerede boot-skaermen foer fejlen kunne vises. Bjoern: «jeg kan ikk
// åbene den i min browser».
//
// Serveren havde vejen hele tiden — /api/auth/login, /api/auth/google/start og
// /api/auth/google/result er public. Det der manglede var en side der brugte
// dem, og et sted at gemme svaret.
//
// Samme flow som desk (SetupScreen.tsx), saa der ikke opstaar en tredje
// variant af «saadan logger man ind».

const NOEGLE = 'jarvis.ui.token'

/** Navnet paa den WS-subprotokol der baerer tokenet. Skal matche
 *  `core/runtime/ws_auth.SUBPROTOKOL` — to steder, ét navn. */
export const WS_SUBPROTOKOL = 'jarvis-bearer'

export function hentToken() {
  try {
    return String(localStorage.getItem(NOEGLE) || '')
  } catch {
    // Private vinduer og blokeret site-data kaster paa selve opslaget.
    return ''
  }
}

/** Gemmer tokenet og siger til hvis det IKKE overlevede.
 *
 *  Foerste udgave slugte fejlen tavst. Da login genindlaeser siden, ville et
 *  mislykket gem betyde at man landede paa login igen uden nogen forklaring —
 *  praecis den tavse fejl resten af dagen gik med at rydde op i. Sker i
 *  private vinduer og naar site-data er blokeret.
 *
 *  Returnerer true naar tokenet kan laeses tilbage. Skriv-fejlen alene er ikke
 *  nok at gaa efter: nogle browsere accepterer skrivningen og kasserer den. */
export function gemToken(token) {
  const t = String(token || '')
  try {
    localStorage.setItem(NOEGLE, t)
  } catch {
    return false
  }
  return hentToken() === t
}

export function glemToken() {
  try {
    localStorage.removeItem(NOEGLE)
  } catch {
    /* ingen */
  }
}

/** Authorization-headeren, eller ingenting hvis vi ikke har et token. */
export function authHeaders() {
  const t = hentToken()
  return t ? { Authorization: `Bearer ${t}` } : {}
}

/** Er fejlen et «du er ikke logget ind»? Bruges til at vise login i stedet
 *  for en raa fejltekst. Serveren svarer 401 med detail «authentication
 *  required»; requestJson pakker den som `${path}: ${detail}`. */
export function erUautoriseret(fejl) {
  const s = String((fejl && fejl.message) || fejl || '')
  return (s.includes('401')
    || s.includes('authentication required')
    || s.includes('ikke logget ind'))
}

// ── Google-login, samme kontrakt som desk ────────────────────────────────
// start → {authorize_url, nonce}; aabn vinduet; poll result indtil ok.

export async function googleStart(appId = 'web-ui') {
  const r = await fetch(`/api/auth/google/start?app_id=${encodeURIComponent(appId)}`)
  return r.json()
}

export async function googleResultat(nonce) {
  const r = await fetch(`/api/auth/google/result?nonce=${encodeURIComponent(nonce)}`)
  return r.json()
}

/** Login med email + password. Public rute. */
export async function loginMedKode(email, password) {
  const r = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  return r.json()
}
