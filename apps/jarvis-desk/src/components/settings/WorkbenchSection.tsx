import { useSettingsResource } from '../../hooks/useSettingsResource'
import { SettingsState, SettingsActionError } from './SettingsState'
import { useState } from 'react'
import { Radio, RotateCcw } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  getCheckpoints,
  getOperatorChannel,
  getRuntimeSwitches,
  rollbackCheckpoint,
  setOperatorChannel,
  setRuntimeSwitch,
} from '../../lib/coworkApi'

/** Adgang til denne computer, fortryd-runde og runtime-kontakter (6/9-2026).
 *
 *  Alle tre var bygget som værktøjer Jarvis kunne kalde, men uden UI kunne
 *  Bjørn hverken se eller styre dem. For kanalen er det et sikkerhedsspørgsmål:
 *  mens den er åben kører `bash` på HANS maskine uden godkendelse pr. kald, i
 *  op til fire timer — og han havde ingen måde at opdage det på.
 */
export function WorkbenchSection(
  { config, sessionId }: { config: ApiConfig | undefined; sessionId?: string | null },
) {
  const channel = useSettingsResource(config, getOperatorChannel)
  const checkpoints = useSettingsResource(config, cfg => getCheckpoints(cfg, sessionId ?? undefined), sessionId ?? '')
  const switches = useSettingsResource(config, getRuntimeSwitches)
  const kanal = channel.data
  const punkter = checkpoints.data?.punkter ?? []
  const kontakter = switches.data
  const [besked, setBesked] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const change = async (action: () => Promise<unknown>, refresh: () => void) => {
    if (busy) return
    setBusy(true); setActionError(''); setBesked('')
    try { await action(); refresh() }
    catch { setActionError('Handlingen kunne ikke gennemføres. Prøv igen.') }
    finally { setBusy(false) }
  }
  const skiftKanal = (aaben: boolean) => config && change(() => setOperatorChannel(config, aaben), channel.retry)
  const fortryd = () => config && change(async () => {
    const result = await rollbackCheckpoint(config, sessionId ?? undefined)
    if (result.status !== 'ok') throw new Error('rollback failed')
    setBesked(`Rullet tilbage til ${result.gendannet}`)
  }, checkpoints.retry)
  const skiftKontakt = (navn: 'bash_sandbox' | 'env_block', on: boolean) => config && change(
    () => setRuntimeSwitch(config, navn, on), switches.retry,
  )

  const timer = kanal?.udloeber_om_s ? Math.round(kanal.udloeber_om_s / 3600) : 0

  return (
    <div className="settings-section workbench-section">
      <h3>Styring af arbejdet</h3>
      <SettingsActionError message={actionError} />
      <SettingsState status={channel.status} label="adgang til denne computer" onRetry={channel.retry} />

      {kanal && <div className={kanal?.open ? 'wb-channel aaben' : 'wb-channel'}>
        <Radio size={14} />
        <div className="wb-channel-text">
          <strong>Adgang til denne computer</strong>
          <span>
            {kanal?.open
              ? `Åben — bash kører på DIN maskine uden godkendelse pr. kald. Lukker om ca. ${timer} t.`
              : 'Lukket — bash kører på serveren.'}
          </span>
        </div>
        <button type="button" disabled={busy} onClick={() => void skiftKanal(!kanal?.open)}>
          {kanal?.open ? 'Luk' : 'Åbn'}
        </button>
      </div>}

      <SettingsState status={checkpoints.status} label="fortrydelsespunkter" onRetry={checkpoints.retry} />
      {checkpoints.data && <div className="wb-checkpoints">
        <div className="wb-row-head">
          <strong>Fortryd redigeringsrunde</strong>
          <button type="button" disabled={busy || punkter.length === 0} onClick={() => void fortryd()}>
            <RotateCcw size={13} /> Fortryd seneste
          </button>
        </div>
        {punkter.length === 0
          ? <div className="cowork-empty">Intet at fortryde i denne session.</div>
          : (
            <ul className="wb-cp-list">
              {punkter.slice(0, 5).map((p) => (
                <li key={p.sha}><code>{p.sha}</code> {p.note}</li>
              ))}
            </ul>
          )}
        {besked && <div className="wb-besked">{besked}</div>}
      </div>}

      <SettingsState status={switches.status} label="arbejdsindstillinger" onRetry={switches.retry} />
      {kontakter && (
        <div className="wb-switches">
          <label>
            <input
              type="checkbox" disabled={busy}
              checked={kontakter.env_block.tændt}
              onChange={(e) => void skiftKontakt('env_block', e.target.checked)}
            />
            Vis Jarvis arbejdsmappe, Git-gren og ugemte ændringer
          </label>
          <label title={kontakter.bash_sandbox.note}>
            <input
              type="checkbox" disabled={busy}
              checked={kontakter.bash_sandbox.tændt}
              onChange={(e) => void skiftKontakt('bash_sandbox', e.target.checked)}
            />
            Begræns terminalkommandoer med en sandkasse
            <span className="settings-hint"> — {kontakter.bash_sandbox.note}</span>
          </label>
        </div>
      )}
    </div>
  )
}
