import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../lib/api'
import {
  opretSideTask, opdaterSideTask,
  type AutonomiMode, type SideTask, type SideTaskRegler,
} from '../lib/sideTasksApi'
import '../styles/side-opgave-dialog.css'

/**
 * Opret — eller redigér — en sideopgave. I en boks midt på skærmen.
 *
 * Bjørn 15/10-2026: «jeg mangler et sted i desk jeg kan oprette side-opgaver
 * selv». Han har selv beskrevet formen, og den er fulgt: en
 * `/side <opgave>`-kommando i composeren OG en «Opret side-opgave»-post i
 * miljø-feltet under «Opret pull request» — begge åbner denne boks.
 *
 * ## Redigering (25/10-2026)
 *
 * Bjørn: «jeg har ikke mulighed for at redigere en eksisterende opgave eller
 * saette regler eller autonomi eller anden.. der er kun title og beskrivelse».
 * Foer denne fandtes kun opret og luk, saa en tastefejl kostede en ny opgave
 * og en gammel der skulle ryddes op. Gives `opgave`, redigerer boksen den i
 * stedet — samme felter, samme validering, ét kald til en anden rute.
 *
 * ## Autonomi er en autorisation, ikke en indstilling
 *
 * Derfor staar betydningen under valget i klartekst frem for kun vaerdien.
 * `local_write` betyder at opgaven maa SKRIVE FILER i Bjørns navn uden at
 * nogen spoerger igen — det er samme slags beslutning som `Approved-By` i en
 * commit, og den skal ikke se ud som en farve man vaelger.
 *
 * Formen er lånt fra `PrivacyDialog` frem for opfundet: native `<dialog>` +
 * `showModal()`, backdrop-klik lukker, og fokus gendannes til det element der
 * havde det. Se `privacy-dialog.css` for hvorfor `margin: auto` er nødvendigt
 * — husets `* { margin: 0 }`-reset i `tokens.css` slår UA'ens centrering, og
 * uden den lander boksen i øverste venstre hjørne.
 */
export function SideOpgaveDialog({
  config, startTekst = '', opgave, onClose, onOprettet,
}: {
  config?: ApiConfig
  /** Teksten efter `/side` — forudfylder beskrivelsen. */
  startTekst?: string
  /** Givet = redigér denne opgave i stedet for at oprette en ny. */
  opgave?: SideTask
  onClose: () => void
  /** Kaldes med den nye opgaves id, så kalderen kan vise den straks. */
  onOprettet?: (sideTaskId: string) => void
}) {
  const ref = useRef<HTMLDialogElement>(null)
  const titelRef = useRef<HTMLInputElement>(null)
  const redigerer = Boolean(opgave)
  const [titel, setTitel] = useState(opgave?.title ?? '')
  const [beskrivelse, setBeskrivelse] = useState(opgave?.prompt ?? startTekst)
  const [autonomi, setAutonomi] = useState<AutonomiMode>(
    (opgave?.autonomy_mode as AutonomiMode) ?? 'none',
  )
  const [minutter, setMinutter] = useState(String(opgave?.max_minutes ?? 20))
  const [kald, setKald] = useState(String(opgave?.max_tool_calls ?? 12))
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

  const gem = async () => {
    if (travl) return
    const t = titel.trim()
    const b = beskrivelse.trim()
    // Serveren afviser også (`flag` kræver begge). Vi siger det her i stedet
    // for at lade et tomt felt blive en rundtur til serveren og tilbage.
    if (!t || !b) { setFejl('Både titel og beskrivelse skal udfyldes'); return }
    if (!config) { setFejl('Ingen forbindelse til serveren'); return }
    setTravl(true); setFejl('')
    // Budgetterne er tekstfelter, så et tomt felt må ikke blive `NaN` — det
    // ville sende `null` til serveren og blive klemt til sin default uden at
    // sige det.
    const regler: SideTaskRegler = {
      autonomy_mode: autonomi,
      max_minutes: Number(minutter) || 20,
      max_tool_calls: Number(kald) || 12,
    }
    try {
      if (redigerer && opgave) {
        await opdaterSideTask(config, opgave.side_task_id, {
          title: t, prompt: b, ...regler,
        })
      } else {
        const id = await opretSideTask(config, t, b, '', regler)
        onOprettet?.(id)
      }
      onClose()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke gemme sideopgaven')
    } finally { setTravl(false) }
  }

  return (
    <dialog
      ref={ref}
      className="sod"
      aria-label={redigerer ? 'Redigér sideopgave' : 'Opret sideopgave'}
      data-testid="side-opgave-dialog"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <div className="sod-indi">
        <button type="button" className="sod-luk" aria-label="Luk" onClick={onClose}>
          <X size={18} />
        </button>
        <h2 className="sod-overskrift">
          {redigerer ? 'Redigér sideopgave' : 'Opret sideopgave'}
        </h2>
        <p className="sod-hint">
          {redigerer
            ? 'Opgaven er ikke taget op endnu, så den kan stadig rettes. Er den i gang, læser et run den lige nu — og så afviser serveren ændringen.'
            : 'Noget du vil have gjort, men ikke nu. Den lægges i køen og forstyrrer ikke den samtale du er i.'}
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
            rows={6}
            maxLength={12000}
            placeholder="Selvstændig instruks — den der tager den senere har ikke denne samtale."
            onChange={(e) => setBeskrivelse(e.target.value)}
          />
        </label>

        <label className="sod-felt" htmlFor="sod-autonomi">
          <span>Autonomi</span>
          <select
            id="sod-autonomi"
            value={autonomi}
            onChange={(e) => setAutonomi(e.target.value as AutonomiMode)}
          >
            <option value="none">Ingen — den venter på mig</option>
            <option value="inspect">Må undersøge — læse og måle, intet ændres</option>
            <option value="local_write">Må skrive filer — i dit navn, uden at spørge</option>
          </select>
        </label>
        {/* Forklaringen staar UDEN FOR label'en: den er ikke feltets navn, og
            laa den inde, ville en skaermlaeser laese hele afsnittet som navn. */}
        <small className="sod-forklaring">
          {autonomi === 'none'
            ? 'En påmindelse. Den står i køen og i min prompt, men starter intet selv.'
            : autonomi === 'inspect'
              ? 'Jeg må læse, søge og måle når jeg er ledig — men ikke ændre noget.'
              : 'Jeg må skrive filer uden at spørge først. Vælg det kun til arbejde du ville have godkendt alligevel.'}
        </small>

        {autonomi !== 'none' ? (
          <div className="sod-budget">
            <label className="sod-felt sod-felt--lille">
              <span>Minutter</span>
              <input
                type="number" min={5} max={60} value={minutter}
                onChange={(e) => setMinutter(e.target.value)}
              />
            </label>
            <label className="sod-felt sod-felt--lille">
              <span>Værktøjskald</span>
              <input
                type="number" min={3} max={40} value={kald}
                onChange={(e) => setKald(e.target.value)}
              />
            </label>
          </div>
        ) : null}

        {fejl ? <p className="sod-fejl" role="alert">{fejl}</p> : null}

        <div className="sod-knapper">
          <button type="button" className="sod-knap" onClick={onClose} disabled={travl}>
            Annullér
          </button>
          <button type="button" className="sod-knap sod-primaer" onClick={() => void gem()} disabled={travl}>
            {travl
              ? (redigerer ? 'Gemmer…' : 'Opretter…')
              : (redigerer ? 'Gem ændringer' : 'Opret sideopgave')}
          </button>
        </div>
      </div>
    </dialog>
  )
}
