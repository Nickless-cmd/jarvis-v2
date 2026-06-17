import { useEffect, useState } from 'react'

/** EU AI Act Art. 50(1): brugeren skal vide de interagerer med AI.
 *  Vises én gang ved første kørsel; valget huskes i localStorage.
 *  Rent additivt — rører hverken backend eller stream. */

const ACK_KEY = 'jarvis-desk:ai-notice-v1'

function alreadyAcked(): boolean {
  try {
    return localStorage.getItem(ACK_KEY) === '1'
  } catch {
    return false
  }
}

export function AiTransparencyNotice() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    if (!alreadyAcked()) setShow(true)
  }, [])

  if (!show) return null

  const ack = () => {
    try {
      localStorage.setItem(ACK_KEY, '1')
    } catch {
      /* ignore — vis bare ikke igen i denne session */
    }
    setShow(false)
  }

  return (
    <div className="ai-notice-overlay" role="dialog" aria-modal="true" aria-labelledby="ai-notice-title">
      <div className="ai-notice-card">
        <div className="ai-notice-badge">AI</div>
        <h2 id="ai-notice-title">Du taler med en AI</h2>
        <p>
          Jarvis er en kunstig intelligens. Svar genereres af en sprogmodel og kan
          indeholde fejl — vurdér selv vigtige beslutninger.
        </p>
        <ul className="ai-notice-points">
          <li>Du godkender selv enhver handling der rører dine data eller sender noget.</li>
          <li>Du kan altid stoppe et svar undervejs.</li>
          <li>Data behandles lokalt hvor muligt; cloud-modeller bruges kun når du vælger dem.</li>
        </ul>
        <button type="button" className="ai-notice-ok" onClick={ack}>
          Forstået
        </button>
      </div>
    </div>
  )
}
