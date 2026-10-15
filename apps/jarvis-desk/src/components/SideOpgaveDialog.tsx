import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import { opretSideTask } from '../lib/sideTasksApi'
import '../styles/side-opgave-dialog.css'

/**
 * Opret en sideopgave — i en boks midt på skærmen.
 *
 * Bjørn 15/10-2026: «jeg mangler et sted i desk jeg kan oprette side-opgaver
 * selv». Han har selv beskrevet formen, og den er fulgt: en
 * `/side <opgave>`-kommando i composeren OG en «Opret side-opgave»-post i
 * miljø-feltet under «Opret pull request» — begge åbner denne boks.
 *
 * Formen er lånt fra `PrivacyDialog` frem for opfundet: native `<dialog>` +
 * `showModal()`, backdrop-klik lukker, og fokus gendannes til det element der
 * havde det. Se `privacy-dialog.css` for hvorfor `margin: auto` er nødvendigt
 * — husets `* { margin: 0 }`-reset i `tokens.css` slår UA'ens centrering, og
 * uden den lander boksen i øverste venstre hjørne.
 *
 * `startTekst` er det man skrev EFTER `/side`. Den forudfylder beskrivelsen,
 * så kommandoen ikke er en omvej til det samme felt man alligevel skulle
 * udfylde.
 */
export function SideOpgaveDialog({
  config, startTekst = '', onClose, onOprettet,
}: {
  config?: ApiConfig
  /** Teksten efter `/side` — forudfylder beskrivelsen. */
  startTekst?: string
  onClose: () => void
  /** Kaldes med den nye opgaves id, så kalderen kan vise den straks. */
  onOprettet?: (sideTaskId: string) => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titelRef = useRef<HTMLInputElement>(null)
  const [titel, setTitel] = useState('')
  const [beskrivelse, setBeskrivelse] = useState(startTekst)
  const [fejl, setFejl] = useState('')
  const [travl, setTravl] = useState(false)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const dialog = ref.current
    if (dialog?.showModal) dialog.showModal()
    else dialog?.setAttribute('open', '')
    // Fokus i TITELEN, ikke i beskrivelsen: har man skrevet `/side noget`, er
    // det ene ord der mangler titlen — og beskrivelsen er allerede udfyldt.
    titelRef.current?.focus()
    return () => { dialog?.close?.(); previous?.focus() }
  }, [])

  const opret = async () => {
    if (travl) return
    const t = titel.trim()
    const b = beskrivelse.trim()
    // Serveren afviser også (`flag` kræver begge). Vi siger det her i stedet
    // for at lade et tomt felt blive en rundtur til serveren og tilbage.
    if (!t || !b) { setFejl('Både titel og beskrivelse skal udfyldes'); return }
    if (!config) { setFejl('Ingen forbindelse til serveren'); return }
    setTravl(true); setFejl('')
    try {
      const id = await opretSideTask(config, t, b)
      onOprettet?.(id)
      onClose()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke oprette sideopgaven')
    } finally { setTravl(false) }
  }

  return (
    <dialog
      ref={ref}
      className="sod"
      aria-label="Opret sideopgave"
      data-testid="side-opgave-dialog"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <div className="sod-indi">
        <button type="button" className="sod-luk" aria-label="Luk" onClick={onClose}>
          <X size={18} />
        </button>
        <h2 className="sod-overskrift">Opret sideopgave</h2>
        <p className="sod-hint">
          Noget du vil have gjort, men ikke nu. Den lægges i køen og forstyrrer
          ikke den samtale du er i.
        </p>

        <label className="sod-felt">
          <span>Titel</span>
          <input
            ref={titelRef}
            type="text"
            value={titel}
            maxLength={200}
            placeholder="Kort imperativ, fx «Ret CI-badgen»"
            onChange={(e) => setTitel(e.target.value)}
          />
        </label>

        <label className="sod-felt">
          <span>Beskrivelse</span>
          <textarea
            value={beskrivelse}
            rows={8}
            maxLength={12000}
            placeholder="Selvstændig instruks — den der tager den senere har ikke denne samtale."
            onChange={(e) => setBeskrivelse(e.target.value)}
          />
        </label>

        {fejl ? <p className="sod-fejl" role="alert">{fejl}</p> : null}

        <div className="sod-knapper">
          <button type="button" className="sod-knap" onClick={onClose} disabled={travl}>
            Annullér
          </button>
          <button type="button" className="sod-knap sod-primaer" onClick={() => void opret()} disabled={travl}>
            {travl ? 'Opretter…' : 'Opret sideopgave'}
          </button>
        </div>
      </div>
    </dialog>
  )
}
