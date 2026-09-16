import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

const getGitStatus = vi.fn()
vi.mock('../../lib/api', async (orig) => ({ ...(await orig() as object), getGitStatus: (...a: unknown[]) => getGitStatus(...a) }))

import { EnvironmentPanel } from './EnvironmentPanel'
const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('EnvironmentPanel', () => {
  beforeEach(() => getGitStatus.mockReset())

  it('vises ikke når der ikke køres', () => {
    const { container } = render(<EnvironmentPanel config={cfg} kind="container" root="/r" working={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('vises under run med branch + ændringer + session-totaler', async () => {
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 3, added: 12, removed: 4 })
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working workingStep="redigerer fil"
      totalTokens={420} totalToolCalls={7}
      evidence={{
        tools: [{ id: 't1', name: 'operator_bash', input: { command: 'git status' }, status: 'done' }],
        sources: [], agents: [],
      }} />)
    expect(screen.getByText('Miljø')).toBeInTheDocument()
    expect(screen.getByText('redigerer fil')).toBeInTheDocument()
    expect(screen.getByText(/420 tokens/)).toBeInTheDocument()
    expect(screen.getByText(/7 kald/)).toBeInTheDocument()
    // operator_bash formateres som "Terminal: git status" (ikke rå navn)
    expect(screen.getByText('Terminal: git status')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('main')).toBeInTheDocument())
    expect(screen.getByText('+12')).toBeInTheDocument()
  })

  it('viser en ren workspace som Ingen ændringer', async () => {
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 0, added: 0, removed: 0 })
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working />)
    expect(await screen.findByText('Ingen ændringer')).toBeInTheDocument()
  })

  it('viser faktiske kilder og åbner dem i inspectoren', async () => {
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 0, added: 0, removed: 0 })
    const source = { url: 'https://docs.example.com/api', domaene: 'docs.example.com', origin: 'tool_result' as const }
    const open = vi.fn()
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], agents: [], sources: [source] }} onOpenSource={open} />)
    await userEvent.click(screen.getByRole('button', { name: 'docs.example.com' }))
    expect(open).toHaveBeenCalledWith(source)
  })
})

describe('EnvironmentPanel — agent-rækker og halen', () => {
  beforeEach(() => {
    getGitStatus.mockReset()
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 0, added: 0, removed: 0 })
  })

  const kald = (id: string) => ({ id, name: 'explore', input: { prompt: 'find noget' }, status: 'running' as const })

  it('en agent UDEN id åbner sit tool-kald, ikke en tom agent-detalje', async () => {
    const aabnAgent = vi.fn()
    const aabnTool = vi.fn()
    const tool = kald('t1')
    const { container } = render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [tool], sources: [], agents: [{ agentId: '', goal: 'find noget', status: 'running', dispatchToolUseId: 't1' }] }}
      onOpenAgent={aabnAgent} onOpenTool={aabnTool} />)
    // Agent-RAEKKEN, ikke tool-chippen — begge baerer opgaveteksten.
    const raekke = container.querySelector('.env-rows .env-row-button:not([disabled])')
    await userEvent.click(raekke as HTMLElement)
    // Detaljen findes ikke — at kalde agent-inspectoren ville give et tomt panel.
    expect(aabnAgent).not.toHaveBeenCalled()
    expect(aabnTool).toHaveBeenCalledWith(tool)
  })

  it('en kørende agent uden id vises som kører', async () => {
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [kald('t1')], sources: [], agents: [{ agentId: '', status: 'running', dispatchToolUseId: 't1' }] }} />)
    expect(await screen.findByText('kører')).toBeInTheDocument()
  })

  it('siger hvor mange kilder der ER, ikke kun hvor mange der vises', async () => {
    const sources = Array.from({ length: 12 }, (_, i) => ({
      url: `https://kilde-${i}.dk/side`, domaene: `kilde-${i}.dk`, origin: 'assistant_text' as const,
    }))
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], agents: [], sources }} />)
    expect(await screen.findByText(/8 af 12/)).toBeInTheDocument()
  })

  it('en agents farve følger agenten, ikke dens plads i listen', async () => {
    const agent = { agentId: 'a1', role: 'researcher', dispatchToolUseId: 't1' }
    const farve = (el: HTMLElement) => el.style.color
    const { unmount } = render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], sources: [], agents: [agent] }} />)
    const alene = farve(await screen.findByText('researcher'))
    unmount()

    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], sources: [], agents: [
        { agentId: 'a0', role: 'foran-1', dispatchToolUseId: 't0' },
        { agentId: 'a2', role: 'foran-2', dispatchToolUseId: 't2' },
        agent,
      ] }} />)
    expect(farve(await screen.findByText('researcher'))).toBe(alene)
  })
})

describe('EnvironmentPanel — hvad git-linjen tør påstå', () => {
  beforeEach(() => getGitStatus.mockReset())

  it('siger IKKE «ikke et git-repo» når det er broen der er nede', async () => {
    getGitStatus.mockResolvedValue({ is_git: false, branch: '', dirty: 0, added: 0, removed: 0, link: 'nede' })
    render(<EnvironmentPanel config={cfg} kind="workstation" root="/r" working />)
    expect(await screen.findByText('Broen er nede')).toBeInTheDocument()
    expect(screen.queryByText('Ikke et git-repo')).not.toBeInTheDocument()
  })

  it('skelner «genforbinder» fra «nede» — en desk der genstarter er ikke væk', async () => {
    getGitStatus.mockResolvedValue({ is_git: false, branch: '', dirty: 0, added: 0, removed: 0, link: 'genforbinder' })
    render(<EnvironmentPanel config={cfg} kind="workstation" root="/r" working />)
    expect(await screen.findByText('Genforbinder…')).toBeInTheDocument()
  })

  it('en mappe UDEN git er stadig «ikke et git-repo»', async () => {
    getGitStatus.mockResolvedValue({ is_git: false, branch: '', dirty: 0, added: 0, removed: 0, link: 'ok' })
    render(<EnvironmentPanel config={cfg} kind="workstation" root="/r" working />)
    expect(await screen.findByText('Ikke et git-repo')).toBeInTheDocument()
  })

  it('fem nye filer vises som fem filer — ikke som +0 −0', async () => {
    // dirty kommer fra `git status --porcelain` (med utrackede), added/removed
    // fra `git diff --numstat HEAD` (kun trackede). De to er ikke samme mængde.
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 5, added: 0, removed: 0, link: 'ok' })
    render(<EnvironmentPanel config={cfg} kind="workstation" root="/r" working />)
    expect(await screen.findByText('5 nye filer')).toBeInTheDocument()
    expect(screen.queryByText('+0')).not.toBeInTheDocument()
  })
})
