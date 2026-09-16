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

  it('viser fire kilder og siger hvor mange der ER i alt', async () => {
    // Aendret 16/9-2026: fire linjer + «Vis alle», ikke otte med et tal i
    // overskriften. Tallet flyttede MED over paa knappen — halen maa aldrig
    // vaere skjult uden at man kan se at den findes.
    const sources = Array.from({ length: 12 }, (_, i) => ({
      url: `https://kilde-${i}.dk/side`, domaene: `kilde-${i}.dk`, origin: 'assistant_text' as const,
    }))
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], agents: [], sources }} />)
    expect(await screen.findByRole('button', { name: 'Vis alle 12' })).toBeInTheDocument()
    expect(screen.getAllByText(/^kilde-\d+\.dk$/)).toHaveLength(4)
  })

  it('«Vis alle» folder hele halen ud og kan foldes sammen igen', async () => {
    const sources = Array.from({ length: 12 }, (_, i) => ({
      url: `https://kilde-${i}.dk/side`, domaene: `kilde-${i}.dk`, origin: 'assistant_text' as const,
    }))
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], agents: [], sources }} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Vis alle 12' }))
    expect(screen.getAllByText(/^kilde-\d+\.dk$/)).toHaveLength(12)
    await userEvent.click(screen.getByRole('button', { name: 'Vis færre' }))
    expect(screen.getAllByText(/^kilde-\d+\.dk$/)).toHaveLength(4)
  })

  it('under fem kilder giver ingen knap — der er ingen hale at folde ud', async () => {
    const sources = Array.from({ length: 3 }, (_, i) => ({
      url: `https://kilde-${i}.dk/side`, domaene: `kilde-${i}.dk`, origin: 'assistant_text' as const,
    }))
    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], agents: [], sources }} />)
    await screen.findByText('kilde-0.dk')
    expect(screen.queryByRole('button', { name: /Vis alle/ })).not.toBeInTheDocument()
  })

  it('en agents farve følger agenten, ikke dens plads i listen', async () => {
    const agent = { agentId: 'a1', role: 'researcher', status: 'active', dispatchToolUseId: 't1' }
    const farve = (el: HTMLElement) => el.style.color
    const { unmount } = render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], sources: [], agents: [agent] }} />)
    const alene = farve(await screen.findByText('researcher'))
    unmount()

    render(<EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], sources: [], agents: [
        { agentId: 'a0', role: 'foran-1', status: 'active', dispatchToolUseId: 't0' },
        { agentId: 'a2', role: 'foran-2', status: 'active', dispatchToolUseId: 't2' },
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

describe('EnvironmentPanel — hvilke agenter står fremme', () => {
  beforeEach(() => {
    getGitStatus.mockReset()
    getGitStatus.mockResolvedValue({ is_git: true, branch: 'main', dirty: 0, added: 0, removed: 0, link: 'ok' })
  })

  const agent = (id: string, status: string) => ({
    agentId: id, role: `rolle-${id}`, status, dispatchToolUseId: `t-${id}`,
  })
  const vis = (agents: ReturnType<typeof agent>[]) => render(
    <EnvironmentPanel config={cfg} kind="container" root="/r" working
      evidence={{ tools: [], sources: [], agents }} />,
  )

  it('en agent der er FÆRDIG forsvinder', async () => {
    vis([agent('a1', 'completed')])
    await screen.findByText('Ingen ændringer')          // panelet ER tegnet
    expect(screen.queryByText('Underagenter')).not.toBeInTheDocument()
    expect(screen.queryByText('rolle-a1')).not.toBeInTheDocument()
  })

  it('en agent der FEJLEDE bliver hængende', async () => {
    vis([agent('a1', 'failed')])
    expect(await screen.findByText('rolle-a1')).toBeInTheDocument()
  })

  it('en agent der ikke stoppede selv (expired) bliver hængende', async () => {
    vis([agent('a1', 'expired')])
    expect(await screen.findByText('rolle-a1')).toBeInTheDocument()
  })

  it('en aktiv agent står fremme', async () => {
    vis([agent('a1', 'active')])
    expect(await screen.findByText('rolle-a1')).toBeInTheDocument()
  })

  it('en pauset agent er ikke færdig og bliver stående', async () => {
    vis([agent('a1', 'suspended')])
    expect(await screen.findByText('rolle-a1')).toBeInTheDocument()
  })

  it('hele feltet forsvinder når alle LØSTE deres opgave', async () => {
    vis([agent('a1', 'completed'), agent('a2', 'succeeded'), agent('a3', 'completed')])
    await screen.findByText('Ingen ændringer')
    expect(screen.queryByText('Underagenter')).not.toBeInTheDocument()
  })

  it('en ANNULLERET agent bliver hængende — den nåede ikke sin opgave', async () => {
    // Bjørns dom 16/9-2026. Jeg havde regnet cancelled som en pæn slutning og
    // spurgte; svaret var nej. Kun det der blev LØST forsvinder.
    vis([agent('a1', 'cancelled')])
    expect(await screen.findByText('rolle-a1')).toBeInTheDocument()
  })

  it('én fejlet blandt ti færdige holder feltet åbent — og viser KUN den ene', async () => {
    vis([...Array.from({ length: 10 }, (_, i) => agent(`ok-${i}`, 'completed')), agent('gik-galt', 'failed')])
    expect(await screen.findByText('Underagenter')).toBeInTheDocument()
    expect(screen.getByText('rolle-gik-galt')).toBeInTheDocument()
    expect(screen.queryByText('rolle-ok-0')).not.toBeInTheDocument()
  })
})
