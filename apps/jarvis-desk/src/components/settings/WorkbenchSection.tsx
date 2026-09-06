import { useEffect, useState } from 'react'
import { Radio, RotateCcw } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import {
  getCheckpoints,
  getOperatorChannel,
  getRuntimeSwitches,
  rollbackCheckpoint,
  setOperatorChannel,
  setRuntimeSwitch,
  type Checkpoint,
  type OperatorChannel,
  type RuntimeSwitches,
} from '../../lib/coworkApi'

/** Operator-kanal, fortryd-runde og runtime-kontakter (6/9-2026).
 *
 *  Alle tre var bygget som værktøjer Jarvis kunne kalde, men uden UI kunne
 *  Bjørn hverken se eller styre dem. For kanalen er det et sikkerhedsspørgsmål:
 *  mens den er åben kører `bash` på HANS maskine uden godkendelse pr. kald, i
 *  op til fire timer — og han havde ingen måde at opdage det på.
 */
export function WorkbenchSection({ config }: { config: ApiConfig | undefined }) {
  const [kanal, setKanal] = useState<OperatorChannel | null>(null)
  const [punkter, setPunkter] = useState<Checkpoint[]>([])
  const [kontakter, setKontakter] = useState<RuntimeSwitches | null>(null)
  const [besked, setBesked] = useState('')

  const load = () => {
    if (!config) return
    getOperatorChannel(config).then(setKanal).catch(() => setKanal(null))
    getCheckpoints(config).then((d) => setPunkter(d.punkter ?? [])).catch(() => setPunkter([]))
    getRuntimeSwitches(config).then(setKontakter).catch(() => setKontakter(null))
  }
  useEffect(load, [config?.apiBaseUrl, config?.authToken])

  const skiftKanal = async (aaben: boolean) => {
    if (!config) return
    setKanal(await setOperatorChannel(config, aaben))
  }
  const fortryd = async () => {
    if (!config) return
    const r = await rollbackCheckpoint(config)
    setBesked(r.status === 'ok' ? `Rullet tilbage til ${r.gendannet}` : (r.error ?? 'Kunne ikke fortryde'))
    load()
  }
  const skiftKontakt = async (navn: 'bash_sandbox' | 'env_block', on: boolean) => {
    if (!config) return
    await setRuntimeSwitch(config, navn, on)
    load()
  }

  const timer = kanal?.udloeber_om_s ? Math.round(kanal.udloeber_om_s / 3600) : 0

  return (
    <div className="settings-section workbench-section">
      <h3>Arbejdsbænk</h3>

      <div className={kanal?.open ? 'wb-channel aaben' : 'wb-channel'}>
        <Radio size={14} />
        <div className="wb-channel-text">
          <strong>Operator-kanal</strong>
          <span>
            {kanal?.open
              ? `Åben — bash kører på DIN maskine uden godkendelse pr. kald. Lukker om ca. ${timer} t.`
              : 'Lukket — bash kører på serveren.'}
          </span>
        </div>
        <button type="button" onClick={() => void skiftKanal(!kanal?.open)}>
          {kanal?.open ? 'Luk' : 'Åbn'}
        </button>
      </div>

      <div className="wb-checkpoints">
        <div className="wb-row-head">
          <strong>Fortryd redigeringsrunde</strong>
          <button type="button" disabled={punkter.length === 0} onClick={() => void fortryd()}>
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
      </div>

      {kontakter && (
        <div className="wb-switches">
          <label>
            <input
              type="checkbox"
              checked={kontakter.env_block.tændt}
              onChange={(e) => void skiftKontakt('env_block', e.target.checked)}
            />
            Fortæl Jarvis hvor han står (mappe, gren, om træet er beskidt)
          </label>
          <label title={kontakter.bash_sandbox.note}>
            <input
              type="checkbox"
              checked={kontakter.bash_sandbox.tændt}
              onChange={(e) => void skiftKontakt('bash_sandbox', e.target.checked)}
            />
            Indespær bash i sandkasse
            <span className="settings-hint"> — {kontakter.bash_sandbox.note}</span>
          </label>
        </div>
      )}
    </div>
  )
}
