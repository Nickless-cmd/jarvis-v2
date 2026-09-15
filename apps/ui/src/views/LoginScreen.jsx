import { useRef, useState } from 'react'
import { gemToken, googleStart, googleResultat, loginMedKode } from '../lib/auth.js'

/**
 * Login til web-UI'en — Google, email+kode, eller et token.
 *
 * Indtil 15/9-2026 fandtes denne skaerm ikke. UI'en sendte ingen legitimation,
 * fik 401 paa hvert kald, og blev staaende paa «Loading unified shell…» for
 * evigt. Bjoern: «jeg kan ikk åbene den i min browser».
 *
 * Flowet er det SAMME som desk (views/SetupScreen.tsx): start → aabn Google i
 * et nyt vindue → poll resultatet. Én maade at logge ind paa, ikke tre.
 * Forskellen er at vi allerede ER i en browser, saa vinduet kan aabnes direkte
 * uden en bro til operativsystemet.
 */
export function LoginScreen({ onLoggedIn }) {
  const [token, setToken] = useState('')
  const [email, setEmail] = useState('')
  const [kode, setKode] = useState('')
  const [travl, setTravl] = useState(false)
  const [besked, setBesked] = useState('')
  const afbrudt = useRef(false)

  const faerdig = (t) => {
    gemToken(t)
    onLoggedIn(t)
  }

  const medGoogle = async () => {
    if (travl) return
    setTravl(true); setBesked('Åbner Google…'); afbrudt.current = false
    try {
      const start = await googleStart('web-ui')
      if (!start.authorize_url || !start.nonce) {
        setBesked('Google-login er ikke sat op på serveren.'); setTravl(false); return
      }
      window.open(start.authorize_url, '_blank', 'noopener,noreferrer')
      setBesked('Log ind i det nye vindue — venter…')
      // Samme taalmodighed som desk: 75 forsoeg à 2 s.
      for (let i = 0; i < 75 && !afbrudt.current; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const res = await googleResultat(start.nonce).catch(() => ({ status: 'pending' }))
        if (res.status === 'ok' && res.token) { faerdig(res.token); return }
        if (res.status === 'error') {
          setBesked(res.error === 'no_account'
            ? 'Ingen J.A.R.V.I.S.-konto er knyttet til den Google-konto.'
            : 'Google-login mislykkedes.')
          setTravl(false); return
        }
      }
      setBesked('Timeout — prøv igen.'); setTravl(false)
    } catch {
      setBesked('Kunne ikke nå serveren.'); setTravl(false)
    }
  }

  const medKode = async () => {
    if (travl) return
    setTravl(true); setBesked('Logger ind…')
    try {
      const r = await loginMedKode(email.trim(), kode)
      if (r && r.token) { faerdig(r.token); return }
      // Sig HVAD der gik galt. En tavs afvisning er grunden til at denne
      // skaerm overhovedet skulle bygges.
      setBesked(r && r.error ? String(r.error) : 'Forkert email eller kode.')
    } catch {
      setBesked('Kunne ikke nå serveren.')
    }
    setTravl(false)
  }

  return (
    <div className="login-skaerm">
      <div className="login-kort">
        <h1>J.A.R.V.I.S.</h1>
        <p className="login-under">Log ind for at åbne fladen</p>

        <button type="button" className="login-google" onClick={medGoogle} disabled={travl}>
          {travl ? 'Forbinder…' : 'Log ind med Google'}
        </button>

        <div className="login-eller">eller</div>

        <label>
          Email
          <input type="email" autoComplete="username" value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Adgangskode
          <input type="password" autoComplete="current-password" value={kode}
                 onChange={(e) => setKode(e.target.value)} />
        </label>
        <button type="button" onClick={medKode} disabled={travl || !email.trim()}>
          Log ind
        </button>

        <details className="login-token">
          <summary>Har du et token?</summary>
          <label>
            Token
            <input type="password" aria-label="token" value={token}
                   onChange={(e) => setToken(e.target.value)} />
          </label>
          <button type="button" onClick={() => faerdig(token.trim())} disabled={!token.trim()}>
            Brug token
          </button>
        </details>

        {besked && <p className="login-besked">{besked}</p>}
      </div>
    </div>
  )
}
