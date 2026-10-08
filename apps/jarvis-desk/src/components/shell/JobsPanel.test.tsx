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
// Kontrakt-agenterne (G) har egne tests i JobsPanel.agents.test.tsx; her er listen tom, så de gamle
// forventninger om jobs-kilderne står uændret.
const getKontraktOverblik = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>('../../lib/agentContractApi')
  return { ...rigtig, getKontraktOverblik: (...a: unknown[]) => getKontraktOverblik(...a) }
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
 *
 * 29/9-2026 — formen blev CC's (B, Bjørn: «dejlig roligt og simplet for
 * uerfaren bruger»): linje 1 er TITLEN (hvad jobbet laver), linje 2 type + ur.
 * Id'et er ude af rækken og lever i `title` + `aria-label`, så to ens job
 * stadig kan skelnes. Derfor bærer mock'erne nedenfor en titel — ikke id'et.
 */
const SERVER = {
  id: 'grid-bot', kilde: 'supervisor' as const, navn: 'grid-bot',
  kommando: 'python3 -m grid_bot --continuous', status: 'running', pid: 1,
  sekunder: 11178, exit_code: null, can_pause: false,
}
const MIN_MASKINE = {
  id: 'bg_a1b2c3d4e5f6', kilde: 'operator' as const, navn: 'Bygger klienten',
  kommando: 'npm run build -- --watch', status: 'running', pid: 4242,
  sekunder: 95, exit_code: null, can_pause: true,
}
const FAERDIG = {
  id: 'gammel', kilde: 'supervisor' as const, navn: 'gammel', kommando: 'ting.sh',
  status: 'exited', pid: null, sekunder: null, exit_code: 1, can_pause: false,
}

beforeEach(() => {
  getKontraktOverblik.mockReset().mockResolvedValue({
    status: 'ok', agents: [], groups: [], contract_version: 'agent-contract-v1',
    capability: { enabled: true, reason: '', contract_version: 'agent-contract-v1' },
    counts: { active: 0, queued: 0, waiting: 0, blocked: 0, attention: 0, open: 0 },
  })
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
    expect(screen.getByText('Bygger klienten')).toBeInTheDocument()
    expect(screen.getByText('Server')).toBeInTheDocument()
    expect(screen.getByText('Din maskine')).toBeInTheDocument()
  })

  it('viser TITLEN i rækken og id-et i tooltip — ikke omvendt', async () => {
    // B (Bjørn 29/9-2026). Kernen: den uerfarne bruger skal ikke læse et
    // shell-id som det første. Id'et er ikke VÆK — det er i `title`, så det
    // stadig kan slås op, og i aria-label, så to ens job kan skelnes.
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    const titel = await screen.findByText('Bygger klienten')
    expect(titel.getAttribute('title')).toBe('bg_a1b2c3d4e5f6 · npm run build -- --watch')
    // Id'et fylder ingenting i rækken — hverken som tekst eller som linje 3.
    expect(screen.queryByText('bg_a1b2c3d4e5f6')).toBeNull()
    expect(screen.queryByText('npm run build -- --watch')).toBeNull()
  })

  it('henter den SAMLEDE liste, ikke kun serverens processer', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await waitFor(() => expect(listJobs).toHaveBeenCalled())
    // Med færdige, ellers ville «Færdige»-sektionen altid være tom.
    // Tredje argument er samtalen (8/10-2026): uden den viste panelet HELE
    // maskinens arbejde, så en anden samtales builds stod her som ens egne.
    // Uden `sessionId`-prop er den `undefined` — og så hentes alt, som før.
    expect(listJobs).toHaveBeenCalledWith(cfg, true, undefined)
  })

  it('sender SAMTALEN med, så panelet ikke viser en anden samtales job', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} sessionId="chat-7" />)
    await waitFor(() => expect(listJobs).toHaveBeenCalled())
    expect(listJobs).toHaveBeenCalledWith(cfg, true, 'chat-7')
  })

  it('en tom samtale med job på maskinen siger det højt', async () => {
    // Samtalen har ingen EGNE job, men maskinen kører. «Ingenting kører» ville
    // være usandt — og det er præcis den forskel panelet findes for at sige.
    listJobs.mockResolvedValue({ jobs: [], bridge_ok: true, uspecificeret: 3 })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} sessionId="chat-7" />)
    expect(await screen.findByText(/Ingen job i denne samtale\. 3 kører på maskinen\./))
      .toBeInTheDocument()
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
    await screen.findByText('Bygger klienten')
    fireEvent.click(screen.getByRole('button', { name: 'Stop Bygger klienten (bg_a1b2c3d4e5f6)' }))
    await waitFor(() => expect(stopJob).toHaveBeenCalledWith(cfg, expect.objectContaining({
      kilde: 'operator', id: 'bg_a1b2c3d4e5f6',
    })))
  })

  it('pause tilbydes kun hvor den kan lade sig gøre', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByText('grid-bot')
    // can_pause=false på serverens job — en knap der ikke virker er værre end ingen.
    expect(screen.queryByRole('button', { name: /^Pause grid-bot/ })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Pause Bygger klienten (bg_a1b2c3d4e5f6)' })).toBeInTheDocument()
  })

  it('en pauset shell kan genoptages', async () => {
    listJobs.mockResolvedValue({ jobs: [{ ...MIN_MASKINE, status: 'paused' }], bridge_ok: true })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Genoptag Bygger klienten (bg_a1b2c3d4e5f6)' }))
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
    id: 'agent-' + 'a'.repeat(32), kilde: 'agent' as const, navn: 'Hvor bor cheap lane-værnet?',
    kommando: 'Scout-agent', status: 'running', pid: null,
    sekunder: 42, exit_code: null, can_pause: false,
  }

  it('en kørende scout vises under «Kører» med spørgsmålet som titel', async () => {
    // B (29/9): spørgsmålet ER hvad agenten laver. «Scout-agent» siger kun
    // hvad den ER, og den tekst lever nu i tooltip — ellers ville linje 3's
    // forsvinden have taget spørgsmålet med sig.
    listJobs.mockResolvedValue({ jobs: [SCOUT], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    const titel = await screen.findByText('Hvor bor cheap lane-værnet?')
    expect(titel.getAttribute('title')).toBe(`agent-${'a'.repeat(32)} · Scout-agent`)
    expect(screen.getByText('Agent')).toBeInTheDocument()
    expect(screen.queryByLabelText(/^Pause /)).toBeNull()
    fireEvent.click(screen.getByLabelText(/^Stop Hvor bor/))
    await waitFor(() => expect(stopJob).toHaveBeenCalledWith(cfg, SCOUT))
  })
})

// ── Åbne shell-sessioner (26/9-2026) ────────────────────────────────────
//
// Bjørn: «hans bash og operator_bash [skal] ramme baggrundsjobs panelet...
// simple vising med en stop knap».
const SHELL_SERVER = {
  id: 'bsh-115cd823bf', kilde: 'shell' as const, navn: "Jarvis' arbejds-shell",
  kommando: "Jarvis' arbejds-shell · tiden er siden sidste kommando startede",
  status: 'running', pid: null, sekunder: 606, exit_code: null, can_pause: false,
}
const SHELL_MIN_MASKINE = {
  id: 'opsess-0123456789ab', kilde: 'shell_operator' as const, navn: 'åben shell',
  kommando: 'åben shell i /media/projects · tiden er siden sidste kommando sluttede',
  status: 'running', pid: null, sekunder: 12, exit_code: null, can_pause: false,
}

describe('åbne shell-sessioner', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('viser en shell på serveren og en på hans maskine som HVER sin maskine', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_SERVER, SHELL_MIN_MASKINE], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    await waitFor(() => expect(screen.getByText("Jarvis' arbejds-shell")).toBeTruthy())
    expect(screen.getByText('åben shell')).toBeTruthy()
    // Linje 2 er HVOR den kører. Uden 'shell_operator' i `kildeNavn` faldt
    // hans egen shell igennem til «Server».
    expect(screen.getByText('Din maskine')).toBeTruthy()
    expect(screen.getByText('Server')).toBeTruthy()
  })

  it('har en stop-knap, men INGEN pause-knap', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_SERVER], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    const stop = await screen.findByLabelText("Stop Jarvis' arbejds-shell (bsh-115cd823bf)")
    // can_pause=false: en kommando i sessionen blokerer kaldet og er loftet
    // til 300 s, saa der er ikke noget oejeblik at pause i.
    expect(screen.queryByLabelText(/^Pause /)).toBeNull()
    fireEvent.click(stop)
    await waitFor(() => expect(stopJob).toHaveBeenCalled())
    // Kilden foelger med, saa ruten ved hvilket vaerktoejs `close` der skal
    // kaldes — daemonens eller operatorens.
    expect(stopJob.mock.calls[0]?.[1].kilde).toBe('shell')
  })

  it('stopper HANS shell gennem operator-kilden, ikke serverens', async () => {
    listJobs.mockResolvedValue({ jobs: [SHELL_MIN_MASKINE], bridge_ok: true })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    fireEvent.click(await screen.findByLabelText('Stop åben shell (opsess-0123456789ab)'))
    await waitFor(() => expect(stopJob).toHaveBeenCalled())
    expect(stopJob.mock.calls[0]?.[1].kilde).toBe('shell_operator')
    expect(stopJob.mock.calls[0]?.[1].id).toBe('opsess-0123456789ab')
  })

  it('viser en shell der KØRER med kommandoen i tooltip og en stop-knap', async () => {
    // Kortet fra Bjørns billede: «Kører / 19m20s / hvad det er». Efter B står
    // «hvad det er» på linje 1, og den fulde kommando i tooltip.
    listJobs.mockResolvedValue({
      jobs: [{
        ...SHELL_SERVER, sekunder: 1160,
        navn: 'kører: npm run build -- --watch',
        kommando: 'kører: npm run build -- --watch',
      }],
      bridge_ok: true,
    })
    render(<JobsPanel config={cfg} onClose={() => {}} isOwner />)
    const titel = await screen.findByText('kører: npm run build -- --watch')
    expect(titel.getAttribute('title')).toBe('bsh-115cd823bf · kører: npm run build -- --watch')
    await waitFor(() => expect(screen.getByText('19m 20s')).toBeTruthy())
    fireEvent.click(screen.getByLabelText(/^Stop /))
    await waitFor(() => expect(stopJob).toHaveBeenCalled())
  })
})

describe('værktøjskald i panelet (3/10-2026)', () => {
  // Bjørn: «alle hans opgaver/bash commandoer bliver vist i baggrunds panelet...
  // det sker ikk på vores?». Rækkerne kommer fra `_tool_jobs` og har `can_stop:
  // false` — der findes ingen rute der kan stoppe et kald inde i et run.
  beforeEach(() => { listJobs.mockReset(); stopJob.mockReset() })

  const KALD = {
    id: 'bash#1791053261', kilde: 'tool' as const,
    navn: 'Kører hele testsuiten',
    kommando: 'bash · npm test -- --run', status: 'running', pid: null,
    sekunder: 137, exit_code: null, can_pause: false, can_stop: false,
  }
  const KALD_HANS = {
    ...KALD, id: 'operator_bash#2', kilde: 'tool_operator' as const,
    navn: 'Kigger i hjemmemaper', sekunder: 45,
  }

  it('viser kaldet med titel, maskine og ur', async () => {
    listJobs.mockResolvedValue({ jobs: [KALD, KALD_HANS], bridge_ok: true })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByText('Kører hele testsuiten')).toBeInTheDocument()
    // Hvert kald sit ur — to rækker må ikke dele ét tal.
    expect(screen.getByText('2m 17s')).toBeInTheDocument()
    expect(screen.getByText('45s')).toBeInTheDocument()
    // To kald, to maskiner: den ene må ikke falde igennem til «Server».
    expect(screen.getByText('Din maskine')).toBeInTheDocument()
  })

  it('tilbyder HVERKEN stop eller pause på et værktøjskald', async () => {
    // Panelet tegner ellers en stop-knap på hver kørende række. Uden
    // `can_stop` fik rækken en knap der så levende ud og gjorde ingenting.
    listJobs.mockResolvedValue({ jobs: [KALD], bridge_ok: true })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByText('Kører hele testsuiten')
    expect(screen.queryByRole('button', { name: /^Stop / })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Pause / })).not.toBeInTheDocument()
  })

  it('en række UDEN can_stop beholder sin stop-knap', async () => {
    // Feltet er en tilføjelse: de hidtidige kilder har det ikke, og de skal
    // ikke miste knappen fordi et nyt felt kom til.
    listJobs.mockResolvedValue({ jobs: [{ ...MIN_MASKINE, can_stop: undefined }], bridge_ok: true })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByRole('button', { name: /^Stop Bygger klienten/ })).toBeInTheDocument()
  })
})
