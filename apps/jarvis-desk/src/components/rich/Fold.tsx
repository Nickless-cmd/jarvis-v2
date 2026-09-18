import { useEffect, useState, type ReactNode } from 'react'

/** Foldens varighed i ms. Skal stemme med transitionen i `app.css` (`.linje-fold`). */
export const FOLD_MS = 200

/**
 * Folder sit indhold ud og ind med højde-animation — og holder det UDE af
 * DOM'en når det er lukket.
 *
 * ## Hvorfor ikke `grid-template-rows: 0fr → 1fr` alene
 *
 * Det er Claude Desktops greb, og det er enklere: kroppen står altid i DOM'en,
 * og CSS'en animerer højden. Men i desk er «foldet = intet i DOM'en» en
 * kontrakt tre steder (runde-, skill- og tanke-linjen), og i en lang tråd
 * ville hver eneste uåbnede runde bære alle sine tool-kort — med diff,
 * output og markdown — i DOM'en.
 *
 * Så her får CSS'en lov at animere, mens indholdet bliver monteret ved første
 * åbning og fjernet igen når folden har lukket. En runde man aldrig har åbnet
 * koster ingenting, og en lukket runde koster ingenting igen bagefter.
 */
export function Fold({ aaben, children }: { aaben: boolean; children: ReactNode }) {
  const [iDom, setIDom] = useState(aaben)

  useEffect(() => {
    if (aaben) {
      setIDom(true)
      return
    }
    if (!iDom) return
    // Luk: lad højden løbe ned FØRST, afmontér bagefter. Ellers ville
    // indholdet forsvinde i samme frame som folden begyndte at lukke.
    const t = setTimeout(() => setIDom(false), FOLD_MS)
    return () => clearTimeout(t)
  }, [aaben, iDom])

  return (
    <div className={`linje-fold${aaben ? ' aaben' : ''}`}>
      <div className="linje-fold-indre">{iDom ? children : null}</div>
    </div>
  )
}
