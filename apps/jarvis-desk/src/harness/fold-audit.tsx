import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/tokens.css'
import '../styles/raekkevisning.css'
import { RaekkeTranskript } from '../components/rich/RaekkeTranskript'
import { MessageRow } from '../components/rich/MessageRow'
import { SettingsProvider } from '../contexts/SettingsContext'
import { RAEKKE_KEY } from '../lib/visningsPref'
import type { ContentBlock } from '../lib/sseProtocol'
localStorage.setItem(RAEKKE_KEY, '1')
const tool = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'bash', input: { command: 'git status' }, status: 'done', result: 'ok' })
const all: ContentBlock[] = [tool('a'), { type: 'text', text: 'TIDLIG SYNTESE. '.repeat(40), phase: 'final_answer', code_answer_protocol: 1 }, { type: 'text', text: 'SLUTBESKEDEN. ' + 'Dette er den oprindelige slutbesked som skal bevares. '.repeat(14), phase: 'final_answer', code_answer_start: true, code_answer_protocol: 1 }, tool('b'), { type: 'text', text: 'SEN SYNTESE A. ', phase: 'commentary', code_answer_protocol: 1 }, tool('c'), { type: 'text', text: 'SEN SYNTESE B.', phase: 'commentary', code_answer_protocol: 1 }]
function Harness() {
 const [stage, setStage] = useState(0)
 const [paced, setPaced] = useState(false)
 ;(window as unknown as { __auditStage: (stage: number) => void }).__auditStage = setStage
 const blocks = stage === 0 ? all.slice(0, 2) : stage === 1 ? all.slice(0, 3) : stage === 4
   ? all.map((b, i) => b.type === 'text' ? { ...b, phase: i === all.length - 1 ? 'final_answer' as const : 'commentary' as const } : b) : all
 const shared = { blocks, streaming: stage < 3, finalAnswerStarted: stage > 0 && stage < 4, runId: 'audit', beskedId: 'audit', arbejdeEfterSvar: stage === 2 }
 return <SettingsProvider><div style={{ maxWidth: 760, padding: 24 }} data-stage={stage} data-paced={String(paced)}>
 {paced ? <MessageRow key="paced" presentation="code" role="assistant" density="compact" {...shared} /> : <RaekkeTranskript {...shared} />}
 <button onClick={() => { setStage(0); setPaced(true) }}>Pacing</button>
 </div></SettingsProvider>
}
createRoot(document.getElementById('root')!).render(<Harness />)
