import { useState, type FormEvent } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  createRoutine, updateRoutine, type Routine, type RoutineCapabilityScope,
  type RoutineDraft, type RoutineTriggerKind,
} from '../../lib/routinesApi'

const inboxEvents = [
  ['created', 'Oprettet og aktiveret'], ['edited', 'Redigeret'], ['paused', 'Pauset eller genoptaget'],
  ['stopped', 'Stoppet eller startet igen'], ['archived', 'Arkiveret eller gendannet'], ['deleted', 'Slettet'],
  ['failed', 'Kørsel fejlede'], ['cancelled', 'Kørsel blev uventet afbrudt'],
  ['action_required', 'Kræver din handling'], ['delivery_failed', 'Levering fejlede permanent'],
  ['retention', 'Automatisk oprydning'],
] as const

export function RoutineEditor({ config, routine, onSaved, onClose }: {
  config: ApiConfig
  routine?: Routine | null
  onSaved: (routine: Routine) => void
  onClose: () => void
}) {
  const [name, setName] = useState(routine?.name ?? '')
  const [instruction, setInstruction] = useState(routine?.instruction ?? '')
  const [capability, setCapability] = useState<RoutineCapabilityScope>(routine?.capability_scope ?? 'chat')
  const [trigger, setTrigger] = useState<RoutineTriggerKind>(routine?.trigger_kind ?? 'manual')
  const [triggerValue, setTriggerValue] = useState(() => {
    const cfg = routine?.trigger_config ?? {}
    return String(cfg.cron ?? cfg.seconds ?? cfg.event ?? '')
  })
  const [inboxPolicy, setInboxPolicy] = useState<Record<string, boolean>>(() => Object.fromEntries(
    inboxEvents.map(([key]) => [key, routine ? routine.inbox_policy[key] !== false : true]),
  ))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!name.trim() || !instruction.trim() || busy) return
    setBusy(true); setError('')
    const trigger_config: Record<string, unknown> = {}
    if (trigger === 'schedule' && triggerValue.trim()) trigger_config.cron = triggerValue.trim()
    if (trigger === 'interval' && triggerValue.trim()) trigger_config.seconds = Number(triggerValue)
    if (trigger === 'event' && triggerValue.trim()) trigger_config.event = triggerValue.trim()
    const draft: RoutineDraft = {
      name: name.trim(), instruction: instruction.trim(), capability_scope: capability,
      trigger_kind: trigger, trigger_config, inbox_policy: { ...(routine?.inbox_policy ?? {}), ...inboxPolicy },
    }
    try {
      const saved = routine
        ? await updateRoutine(config, routine.routine_id, routine.version, draft)
        : await createRoutine(config, draft)
      onSaved(saved)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Rutinen kunne ikke gemmes')
    } finally { setBusy(false) }
  }

  const preserved = routine?.status === 'paused' ? 'Rutinen forbliver pauset efter redigering.'
    : routine?.status === 'stopped' ? 'Rutinen forbliver stoppet efter redigering.' : ''

  return (
    <section className="routine-editor" aria-label={routine ? 'Redigér rutine' : 'Opret rutine'}>
      <header className="routine-editor-head">
        <div role="tablist" aria-label="Rutineeditor">
          <div role="tab" aria-selected="true" className="routine-editor-tab">
            {routine ? 'Redigér rutine' : 'Opret rutine'}
          </div>
        </div>
        <button type="button" className="routine-icon-button" aria-label="Luk editor" onClick={onClose}><X size={17} /></button>
      </header>
      <form className="routine-form" onSubmit={(event) => void submit(event)}>
        <div className="routine-form-intro">
          <h1>{routine ? routine.name : 'Ny rutine'}</h1>
          <p>Rutinen arbejder selvstændigt efter denne definition og skriver relevante hændelser i din inbox.</p>
        </div>
        <label>Navn<input aria-label="Navn" value={name} onChange={(e) => setName(e.target.value)} required /></label>
        <label>Instruktion<textarea aria-label="Instruktion" value={instruction} onChange={(e) => setInstruction(e.target.value)} rows={8} required /></label>
        <div className="routine-form-grid">
          <label>Arbejdsområde<select aria-label="Arbejdsområde" value={capability} onChange={(e) => setCapability(e.target.value as RoutineCapabilityScope)}>
            <option value="chat">Chat</option><option value="code">Code</option>
          </select></label>
          <label>Udløser<select aria-label="Udløser" value={trigger} onChange={(e) => setTrigger(e.target.value as RoutineTriggerKind)}>
            <option value="manual">Manuel</option><option value="schedule">Tidsplan</option>
            <option value="interval">Interval</option><option value="event">Hændelse</option>
          </select></label>
        </div>
        {trigger !== 'manual' && <label>{trigger === 'schedule' ? 'Cron-plan' : trigger === 'interval' ? 'Sekunder' : 'Hændelsesnavn'}
          <input aria-label="Udløserværdi" value={triggerValue} onChange={(e) => setTriggerValue(e.target.value)} />
        </label>}
        <fieldset className="routine-inbox-options">
          <legend>Din inbox</legend>
          <p>Vælg selv hvilke hændelser der skal give en besked. Indholdet leveres aldrig til en anden samtale.</p>
          <div>
            {inboxEvents.map(([key, label]) => <label className="routine-check" key={key}>
              <input type="checkbox" checked={inboxPolicy[key] ?? false}
                onChange={(e) => setInboxPolicy((current) => ({ ...current, [key]: e.target.checked }))} /> {label}
            </label>)}
          </div>
        </fieldset>
        {preserved && <p className="routine-state-note">{preserved}</p>}
        {error && <p className="routine-error" role="alert">{error}</p>}
        <div className="routine-form-actions">
          <button type="button" className="routine-button secondary" onClick={onClose}>Annullér</button>
          <button type="submit" className="routine-button primary" disabled={busy}>
            {routine ? 'Gem ændringer' : 'Gem og aktivér'}
          </button>
        </div>
      </form>
    </section>
  )
}
