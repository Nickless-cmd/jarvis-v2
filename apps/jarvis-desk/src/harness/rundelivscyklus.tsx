/**
 * BROWSER-HARNESS — rundernes visuelle livscyklus i BEGGE tilstande, gennem den
 * produktions-komponent der faktisk tegner en besked (`MessageRow`).
 *
 * `?mode=chat|code`. Forløbet er Syntese A → Runde 1 → Syntese B → Runde 2 →
 * Syntese C. `window.__trin(n)` ruller serveren frem, `window.__persisteret()`
 * remounter som en gemt besked (ingen pacing, ingen streaming).
 *
 * Køres med `npx vite --port 5299` → `/src/harness/rundelivscyklus.html?mode=code`.
 */
import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/tokens.css'
import '../styles/raekkevisning.css'
import { MessageRow } from '../components/rich/MessageRow'
import { SettingsProvider } from '../contexts/SettingsContext'
import { RAEKKE_KEY } from '../lib/visningsPref'
import type { ContentBlock } from '../lib/sseProtocol'

localStorage.setItem(RAEKKE_KEY, '1')
const mode = new URLSearchParams(location.search).get('mode') === 'chat' ? 'chat' : 'code'
const LEN = Number(new URLSearchParams(location.search).get('len') ?? 4)
// A er altid kort: så er paceren færdig med den når R1 ankommer, og R1 er synlig som aktiv linje.
// B og C er lange (`len`): de pacer længe nok til at fadet og overdragelsen kan observeres.
const lang = (navn: string) => `${navn}. ` + 'Dette er en lang syntese der skal pace gennem flere sekunder. '.repeat(navn === 'SYNTESE-A' ? 4 : LEN)
const tool = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'bash', input: { command: `echo ${id}` }, status: 'done', result: 'ok' })
const text = (navn: string, start = false): ContentBlock => ({
  type: 'text', text: lang(navn), phase: start ? 'final_answer' : 'commentary', code_answer_protocol: 1, code_answer_start: start,
})
const ALLE: ContentBlock[] = [tool('r0'), text('SYNTESE-A', true), tool('R1'), text('SYNTESE-B'), tool('R2'), text('SYNTESE-C')]
// trin → antal blokke serveren har sendt (1 = kun arbejde, 2 = slutbeskeden begynder)
const ANTAL = [0, 1, 2, 3, 4, 5, 6]

function Harness() {
  const [trin, setTrin] = useState(0)
  const [slut, setSlut] = useState(false)
  const [persist, setPersist] = useState(false)
  const w = window as unknown as Record<string, unknown>
  w.__trin = (n: number) => { setSlut(false); setTrin(n) }
  w.__serverSlut = () => setSlut(true)
  w.__persisteret = () => setPersist(true)
  const blocks = ALLE.slice(0, ANTAL[trin])
  const streaming = !persist && !slut && trin > 0
  const live = !persist && trin > 0
  return (
    <SettingsProvider>
      <div style={{ maxWidth: 760, padding: 24 }}>
        <MessageRow
          key={persist ? 'gemt' : 'live'}
          role="assistant" presentation={mode} density="compact"
          blocks={persist ? ALLE : blocks}
          streaming={streaming}
          status={streaming ? 'working' : 'done'}
          finalAnswerStarted={!persist && trin > 1}
          arbejdeEfterSvar={false}
          runId="rl-run" turId="rl-tur" beskedId="rl-besked"
          turStart={Date.now() - 5000}
          paceFinalAnswer={live && mode === 'chat'}
          flushFinalAnswer={false}
        />
      </div>
    </SettingsProvider>
  )
}
createRoot(document.getElementById('root')!).render(<Harness />)
