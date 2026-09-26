import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const listJobs = vi.fn()
const stopJob = vi.fn()
const pauseJob = vi.fn()
const resumeJob = vi.fn()
vi.mock('../../lib/jobsApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/jobsApi')>('../../lib/jobsApi')
  return {
    varighed: rigtig.varighed,
    kildeNavn: rigtig.kildeNavn,
    listJobs: (...a: unknown[]) => listJobs(...a),
    stopJob: (...a: unknown[]) => stopJob(...a),
    pauseJob: (...a: unknown[]) => pauseJob(...a),
    resumeJob: (...a: unknown[]) => resumeJob(...a),
  }
})
const removeProcess = vi.fn()
vi.mock('../../lib/processesApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/processesApi')>('../../lib/processesApi')
  return { ...rigtig, removeProcess: (...a: unknown[]) => removeProcess(...a) }
})

import { JobsPanel } from './JobsPanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

/**
 * Det panelet skal kunne, og som det IKKE kunne før 16/9-2026:
 *
 *  1. vise job fra BEGGE maskiner — serverens supervisor og Bjørns egne shells
 *  2. sige forskel på «der kører ingenting» og «jeg kan ikke se din maskine»
 *  3. stoppe et job på den maskine det faktisk kører på
 */
const SERVER = {
  id: 'grid-bot', kilde: 'supervisor' as const, navn: 'grid-bot',
  kommando: 'python3 -m grid_bot --continuous', status: 'running', pid: 1,
  sekunder: 11178, exit_code: null, can_pause: false,
}
const MIN_MASKINE = {
  id: 'bg_a1b2c3d4e5f6', kilde: 'operator' as const, navn: 'bg_a1b2c3d4e5f6',
  kommando: 'npm run build -- --watch', status: 'running', pid: 4242,
  sekunder: 95, exit_code: null, can_pause: true,
}
const FAERDIG = {
  id: 'gammel', kilde: 'supervisor' as const, navn: 'gammel', kommando: 'ting.sh',
  status: 'exited', pid: null, sekunder: null, exit_code: 1, can_pause: false,
}

beforeEach(() => {
  listJobs.mockReset().mockResolvedValue({ jobs: [SERVER, MIN_MASKINE, FAERDIG], bridge_ok: true })
  stopJob.mockReset().mockResolvedValue(undefined)
  pauseJob.mockReset().mockResolvedValue(undefined)
  resumeJob.mockReset().mockResolvedValue(undefined)
  removeProcess.mockReset().mockResolvedValue(undefined)
})

describe('JobsPanel', () => {
  it('viser job fra BEGGE maskiner', async () => {
    // Kernen i fejlen: panelet hentede kun serverens supervisor, så alt Jarvis
    // satte i gang på Bjørns egen maskine var usynligt.
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByText('grid-bot')).toBeInTheDocument()
    expect(screen.getByText('bg_a1b2c3d4e5f6')).toBeInTheDocument()
    expect(screen.getByText('Server')).toBeInTheDocument()
    expect(screen.getByText('Din maskine')).toBeInTheDocument()
  })

  it('henter den SAMLEDE liste, ikke kun serverens processer', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await waitFor(() => expect(listJobs).toHaveBeenCalled())
    // Med færdige, ellers ville «Færdige»-sektionen altid være tom.
    expect(listJobs).toHaveBeenCalledWith(cfg, true)
  })

  it('en død bro er IKKE en tom liste', async () => {
    listJobs.mockResolvedValue({ jobs: [SERVER], bridge_ok: false })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByText(/Kan ikke se din maskine/)).toBeInTheDocument()
    // Serverens job vises stadig — den ene kilde må ikke tage den anden med sig.
    expect(screen.getByText('grid-bot')).toBeInTheDocument()
  })

  it('stop rammer jobbet på DEN maskine det kører på', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByText('bg_a1b2c3d4e5f6')
    fireEvent.click(screen.getByRole('button', { name: 'Stop bg_a1b2c3d4e5f6' }))
    await waitFor(() => expect(stopJob).toHaveBeenCalledWith(cfg, expect.objectContaining({
      kilde: 'operator', id: 'bg_a1b2c3d4e5f6',
    })))
  })

  it('pause tilbydes kun hvor den kan lade sig gøre', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByText('grid-bot')
    // can_pause=false på serverens job — en knap der ikke virker er værre end ingen.
    expect(screen.queryByRole('button', { name: 'Pause grid-bot' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause bg_a1b2c3d4e5f6' })).toBeInTheDocument()
  })

  it('en pauset shell kan genoptages', async () => {
    listJobs.mockResolvedValue({ jobs: [{ ...MIN_MASKINE, status: 'paused' }], bridge_ok: true })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Genoptag bg_a1b2c3d4e5f6' }))
    await waitFor(() => expect(resumeJob).toHaveBeenCalled())
    expect(pauseJob).not.toHaveBeenCalled()
  })

  it('en member ser jobbene, men kan ikke stoppe dem', async () => {
    render(<JobsPanel config={cfg} isOwner={false} onClose={() => {}} />)
    await screen.findByText('grid-bot')
    expect(screen.queryByRole('button', { name: /^Stop / })).not.toBeInTheDocument()
  })

  it('en fejlet hentning vælter ikke panelet', async () => {
    listJobs.mockRejectedValue(new Error('nede'))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByText('kunne ikke hente jobs')).toBeInTheDocument()
    expect(screen.getByText('Ingenting kører lige nu.')).toBeInTheDocument()
  })

  it('melder antal kørende op, så tælleren ikke kan modsige listen', async () => {
    const taeller = vi.fn()
    render(<JobsPanel config={cfg} isOwner onCount={taeller} onClose={() => {}} />)
    await waitFor(() => expect(taeller).toHaveBeenCalledWith(2))   // FAERDIG tæller ikke med
  })

  it('«Ryd færdige» siger hvad den IKKE kunne rydde', async () => {
    listJobs.mockResolvedValue({
      jobs: [FAERDIG, { ...MIN_MASKINE, status: 'exited', exit_code: 0 }], bridge_ok: true,
    })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Ryd færdige' }))
    // Operatørens shells er filer på hans maskine; der findes ingen rute til
    // at slette dem. Knappen må ikke se ud som om den tog dem alle.
    expect(await screen.findByText(/1 shell\(s\) på din maskine kan ikke ryddes/)).toBeInTheDocument()
    expect(removeProcess).toHaveBeenCalledTimes(1)
  })
})

describe('tilstande der ikke er «kører» eller «exit N»', () => {
  it('«lost» vises som mistet — ikke som et gættet exit', async () => {
    listJobs.mockResolvedValue({
      jobs: [{ ...FAERDIG, status: 'lost', exit_code: null }], bridge_ok: true,
    })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: /Færdige/ }))
    expect(await screen.findByText('mistet')).toBeInTheDocument()
  })
})

describe('JobsPanel — belastningen på broen', () => {
  it('starter ikke et nyt opslag mens det forrige er undervejs', async () => {
    // Hvert opslag koerer en kommando paa Bjoerns maskine over broen. Er den
    // langsom, ville en poll hvert 5. sekund lægge kald i kø hos ham.
    vi.useFakeTimers()
    let slip: ((v: unknown) => void) | null = null
    listJobs.mockImplementation(() => new Promise((r) => { slip = r }))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(listJobs).toHaveBeenCalledTimes(1)

    await vi.advanceTimersByTimeAsync(15000)      // tre polls ville vaere fyret
    expect(listJobs).toHaveBeenCalledTimes(1)

    slip!({ jobs: [], bridge_ok: true })
    await vi.advanceTimersByTimeAsync(5000)
    expect(listJobs).toHaveBeenCalledTimes(2)     // og saa maa den igen
    vi.useRealTimers()
  })
})

describe('scout-agenter i panelet (17/9-2026)', () => {
  beforeEach(() => { listJobs.mockReset(); stopJob.mockReset() })

  const SCOUT = {
    id: 'agent-' + 'a'.repeat(32), kilde: 'agent' as const, navn: 'Scout-agent',
    kommando: 'Hvor bor cheap lane-værnet?', status: 'running', pid: null,
    sekunder: 42, exit_code: null, can_pause: false,
  }

  it('en kørende scout vises under «Kører», med «Agent» som kilde og uden pause-knap', async () => {
    listJobs.mockResolvedValue({ jobs: [SCOUT], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    await waitFor(() => expect(screen.getByText('Scout-agent')).toBeInTheDocument())
    expect(screen.getByText('Agent')).toBeInTheDocument()
    expect(screen.getAllByText('Hvor bor cheap lane-værnet?').length).toBeGreaterThan(0)
    expect(screen.queryByLabelText('Pause Scout-agent')).toBeNull()
    fireEvent.click(screen.getByLabelText('Stop Scout-agent'))
    await waitFor(() => expect(stopJob).toHaveBeenCalledWith(cfg, SCOUT))
  })
})

// ── Åbne shell-sessioner (26/9-2026) ────────────────────────────────────
//
// Bjørn: «hans bash og operator_bash [skal] ramme baggrundsjobs panelet...
// simple vising med en stop knap».
const SHELL_SERVER = {
  id: 'bsh-115cd823bf', kilde: 'shell' as const, navn: 'bsh-115cd823bf',
  kommando: 'åben shell · intet kører · tiden er tomgang',
  status: 'running', pid: null, sekunder: 606, exit_code: null, can_pause: false,
}
const SHELL_MIN_MASKINE = {
  id: 'opsess-0123456789ab', kilde: 'shell_operator' as const, navn: 'opsess-0123456789ab',
  kommando: 'åben shell i /media/projects · intet kører · tiden er tomgang',
  status: 'running', pid: null, sekunder: 12, exit_code: null, can_pause: false,
}

describe('åbne shell-sessioner', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('viser en shell på serveren og en på hans maskine som HVER sin maskine', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_SERVER, SHELL_MIN_MASKINE], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    await waitFor(() => expect(screen.getByText('bsh-115cd823bf')).toBeTruthy())
    expect(screen.getByText('opsess-0123456789ab')).toBeTruthy()
    // Linje 2 er HVOR den kører. Uden 'shell_operator' i `kildeNavn` faldt
    // hans egen shell igennem til «Server».
    expect(screen.getByText('Din maskine')).toBeTruthy()
    expect(screen.getByText('Server')).toBeTruthy()
  })

  it('har en stop-knap, men INGEN pause-knap', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_SERVER], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    const stop = await screen.findByLabelText('Stop bsh-115cd823bf')
    // can_pause=false: en kommando i sessionen blokerer kaldet og er loftet
    // til 300 s, saa der er ikke noget oejeblik at pause i.
    expect(screen.queryByLabelText('Pause bsh-115cd823bf')).toBeNull()
    fireEvent.click(stop)
    await waitFor(() => expect(stopJob).toHaveBeenCalled())
    // Kilden foelger med, saa ruten ved hvilket vaerktoejs `close` der skal
    // kaldes — daemonens eller operatorens.
    expect(stopJob.mock.calls[0]?.[1].kilde).toBe('shell')
  })

  it('stopper HANS shell gennem operator-kilden, ikke serverens', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_MIN_MASKINE], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    fireEvent.click(await screen.findByLabelText('Stop opsess-0123456789ab'))
    await waitFor(() => expect(stopJob).toHaveBeenCalled())
    expect(stopJob.mock.calls[0]?.[1].kilde).toBe('shell_operator')
    expect(stopJob.mock.calls[0]?.[1].id).toBe('opsess-0123456789ab')
  })
})
