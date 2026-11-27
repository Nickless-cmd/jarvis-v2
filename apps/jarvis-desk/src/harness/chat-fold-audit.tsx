import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import '../styles/tokens.css'
import '../styles/raekkevisning.css'
import { ChatFlowPresentation } from '../components/rich/ChatFlowPresentation'
import { SettingsProvider } from '../contexts/SettingsContext'
import type { ContentBlock } from '../lib/sseProtocol'
const tool = (id: string): ContentBlock => ({ type: 'tool_use', id, name: 'read_file', input: { path: id + '.txt' }, status: 'done', result: 'ok' })
const text = (value: string, start = false): ContentBlock => ({ type: 'text', text: value, phase: start ? 'final_answer' : 'commentary', code_answer_protocol: 1, code_answer_start: start })
const all = [tool('a'), text('TIDLIG SYNTESE. '.repeat(35)), text('SLUTBESKEDEN. ' + 'Svarteksten skal blive stående. '.repeat(10), true), tool('b'), text('SEN SYNTESE A.'), tool('c'), text('SEN SYNTESE B.')]
function Harness() {
 const [stage, setStage] = useState(0)
 const [paced, setPaced] = useState(false)
 ;(window as unknown as { __auditStage: (stage: number) => void }).__auditStage = setStage
 const blocks = stage === 0 ? all.slice(0, 2) : stage === 1 ? all.slice(0, 3) : all
 return <SettingsProvider><div style={{ maxWidth: 760, padding: 24 }} data-stage={stage}>
 <ChatFlowPresentation key={String(paced)} mode="living" density="compact" blocks={blocks}
   streaming={stage < 3} status={stage < 3 ? 'working' : 'done'} finalAnswerStarted={stage > 0}
   paceFinalAnswer flushFinalAnswer={!paced} runId={paced ? 'chat-audit-paced' : 'chat-audit'} />
 <button onClick={() => { setStage(0); setPaced(true) }}>Pacing</button>
 </div></SettingsProvider>
}
createRoot(document.getElementById('root')!).render(<Harness />)
