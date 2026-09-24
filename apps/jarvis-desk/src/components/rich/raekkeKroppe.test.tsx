import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { kropFor, postFor, udDel, exitKode } from './raekkeKroppe'
import type { ApiConfig } from '../../lib/api'

function vis(
  navn: string,
  input: Record<string, unknown>,
  result?: string,
  fejl = false,
  config?: ApiConfig,
) {
  return render(<>{kropFor(navn, input, result, fejl, config)}</>)
}

describe('rækkevisningens værktøjskroppe', () => {
  it('viser en indlejret operator-læsning som fil med linjenumre frem for JSON', () => {
    const { container } = vis('operator_read_file', { path: '/home/bs/Hentet/a.html' },
      JSON.stringify({ status: 'ok', path: '/home/bs/Hentet/a.html', result: '<title>Før</title>\n<p>Hej</p>' }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(screen.getByText('a.html')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.getByText('<title>Før</title>')).toBeInTheDocument()
    expect(container.textContent).not.toContain('"status"')
    expect(container.textContent).not.toContain('IN')
  })

  it('viser stdout frem for rå JSON når resultatet bærer serverens interne hale', () => {
    // Serveren hæfter en kort instruks på det sidste værktøjs-resultat hver
    // runde (visible_followup_results._NUDGE). Den gemmes med i turen, og så
    // fejlede JSON.parse: kroppen dumpede hele dokumentet i stedet for stdout.
    const raa = JSON.stringify({ result: { platform: 'linux', stdout: 'version: 0.6.86\nBUILD-EXIT=0', exit_code: 0 } })
    const { container } = vis('operator_bash', { command: 'npm run build' },
      `${raa}\n\n(⟳ Før du fortsætter: skriv én kort sætning om hvad disse resultater betyder og hvad du gør nu.)`)
    expect(container.textContent).toContain('BUILD-EXIT=0')
    expect(container.textContent).not.toContain('"platform"')
    expect(container.textContent).not.toContain('⟳')
  })

  it('læser exit-koden selv om halen står bag JSON-en', () => {
    const raa = JSON.stringify({ result: { stdout: 'boom', exit_code: 3 } })
    expect(exitKode(`${raa}\n\n(⟳ Før du fortsætter: noget.)`, false)).toBe(3)
  })

  it('fjerner halen fra et rent tekst-resultat', () => {
    expect(udDel('permission denied\n\n(⟳ Før du fortsætter: noget.)')).toBe('permission denied')
  })

  it('bevarer JSON-filer som filtekst og viser også de sidste linjer', () => {
    const content = ['{"name":"jarvis"}', ...Array.from({ length: 15 }, (_, i) => `line ${i + 2}`)].join('\n')
    const { container } = vis('operator_read_file', { path: 'config.json' },
      JSON.stringify({ status: 'ok', result: content }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(container.textContent).toContain('{"name":"jarvis"}')
    expect(container.textContent).toContain('line 16')
  })

  it('viser også en gyldig JSON-fil på én linje som tekst', () => {
    const { container } = vis('operator_read_file', { path: 'config.json' },
      JSON.stringify({ status: 'ok', result: '{"name":"jarvis"}' }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(container.textContent).toContain('{"name":"jarvis"}')
  })

  it('viser en tom fil som fil frem for et manglende resultat', () => {
    const { container } = vis('operator_read_file', { path: 'empty.txt' },
      JSON.stringify({ status: 'ok', result: '' }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(container.textContent).toContain('empty.txt')
    expect(container.textContent).not.toContain('No file content')
  })

  it('viser den lokale read_file-kontrakt med text direkte i resultatet', () => {
    const { container } = vis('read_file', { path: 'app.ts' },
      JSON.stringify({ status: 'ok', path: 'app.ts', text: 'const app = true' }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(container.textContent).toContain('const app = true')
  })

  it('farver kendt filtype uden at miste linjenumre', async () => {
    const { container } = vis('read_file', { path: 'app.ts' },
      JSON.stringify({ status: 'ok', text: 'const app = true' }))
    await waitFor(() => expect(container.querySelector('.rv-filKode .shiki .line')).toBeInTheDocument(), { timeout: 5000 })
    expect(container.querySelector('.rv-filKode')).toHaveAttribute('data-lang', 'typescript')
    expect(container.querySelector('.rv-filKode .shiki')?.getAttribute('style')).toContain('--shiki-light')
    expect(container.querySelector('.rv-filKode .shiki')?.getAttribute('style')).toContain('--shiki-dark')
  })

  it('viser operator-redigeringens diff_preview som ændrede linjer', () => {
    const { container } = vis('operator_edit_file', { path: '/home/bs/Hentet/a.html', old_string: 'Før', new_string: 'Efter' },
      JSON.stringify({ status: 'ok', result: { replacements: 1, diff_preview: '--- a.html (before)\n+++ a.html (after)\n-<title>Før</title>\n+<title>Efter</title>' } }))
    expect(container.querySelector('.rv-diff')).toBeInTheDocument()
    expect(container.querySelector('[data-k="del"]')?.textContent).toContain('Før')
    expect(container.querySelector('[data-k="add"]')?.textContent).toContain('Efter')
    expect(container.textContent).not.toContain('"replacements"')
  })

  it('opfinder ikke en anvendt diff ud fra argumenter ved ukendt resultat', () => {
    const { container } = vis('edit_file', { path: 'a.txt', old_text: 'før', new_text: 'efter' }, 'permission denied')
    expect(container.querySelector('.rv-diff')).toBeNull()
    expect(container.textContent).toContain('permission denied')
  })

  it('viser skrivning som filforhåndsvisning og målt resultat', () => {
    const { container } = vis('operator_write_file', { path: 'new.ts', content: 'export const n = 1' },
      JSON.stringify({ status: 'ok', result: { bytes_written: 18, was_new_file: true, path: 'new.ts' } }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(screen.getByText('export const n = 1')).toBeInTheDocument()
    expect(container.textContent).toContain('18 bytes')
    expect(container.textContent).not.toContain('"bytes_written"')
  })

  it('viser ikke ønsket filindhold som skrevet ved ubekræftet svar', () => {
    const { container } = vis('write_file', { path: 'new.ts', content: 'export const n = 1' }, 'permission denied')
    expect(container.querySelector('.rv-fil')).toBeNull()
    expect(container.textContent).toContain('permission denied')
  })

  it('viser søgetræffere med fil, linje og tekst', () => {
    const { container } = vis('operator_grep', { pattern: 'title' },
      JSON.stringify({ status: 'ok', result: [{ file: 'a.html', line: 6, text: '<title>Efter</title>' }] }))
    expect(container.textContent).toContain('a.html:6')
    expect(container.textContent).toContain('<title>Efter</title>')
    expect(container.textContent).not.toContain('"file"')
  })

  it('viser filliste og webresultater som læsbare poster', () => {
    const files = vis('operator_glob', { pattern: '*.tsx' },
      JSON.stringify({ status: 'ok', result: ['/repo/App.tsx', '/repo/CodeView.tsx'] }))
    expect(files.container.querySelectorAll('.rv-i')).toHaveLength(2)
    expect(files.container.textContent).toContain('/repo/App.tsx')
    files.unmount()
    const web = vis('web_search', { query: 'Jarvis' },
      JSON.stringify({ results: [{ title: 'Jarvis Docs', url: 'https://example.org/docs' }] }))
    expect(web.container.querySelector('.rv-web')).toBeInTheDocument()
    expect(web.container.textContent).toContain('Jarvis Docs')
  })

  it('mister ikke webresultater der kun er tekststrenge', () => {
    const { container } = vis('web_search', { query: 'Jarvis' },
      JSON.stringify({ results: ['Jarvis docs — https://example.org/docs'] }))
    expect(container.querySelector('.rv-web')).toBeInTheDocument()
    expect(container.textContent).toContain('Jarvis docs')
  })

  it('viser alternative søgefelter uden rå JSON', () => {
    const { container } = vis('search_memory', { query: 'status' },
      JSON.stringify({ matches: [{ path: 'memory.md', line: 12, summary: 'Status er grøn' }] }))
    expect(container.textContent).toContain('memory.md:12')
    expect(container.textContent).toContain('Status er grøn')
    expect(container.textContent).not.toContain('"summary"')
  })

  it('finder listen uanset hvilken nøgle den er pakket i', () => {
    // Målt 23/9-2026: grenen ledte kun efter `matches`, så disse faldt til den
    // generiske feltliste — listen FANDTES, den lå bare bag en nøgle grenen
    // ikke kendte. `process_list` bruger `processes`, wakeups bruger `wakeups`.
    const p = vis('process_list', {},
      JSON.stringify({ count: 1, processes: [{ name: 'watchdog', pid: 42, status: 'running' }] }))
    expect(p.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(p.container.querySelector('.rv-felter')).not.toBeInTheDocument()
    expect(p.container.textContent).toContain('watchdog')

    const w = vis('list_self_wakeups', {},
      JSON.stringify({ status: 'ok', wakeups: [{ prompt: 'tjek CI', status: 'pending' }] }))
    expect(w.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(w.container.textContent).toContain('tjek CI')
  })

  it('graver ét niveau ned efter listen (central_query.data.items)', () => {
    // `central_query` pakker sin liste i `data.items` — dobbelt indpakket.
    const { container } = vis('central_query', { action: 'incidents' },
      JSON.stringify({ action: 'incidents', data: { items: [{ id: 7, kind: 'fan5' }] } }))
    expect(container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(container.textContent).toContain('fan5')
  })

  it('viser en tekststreng med linjer som en liste', () => {
    // `git_log`/`git_status`/`git_diff` sender én streng med linjer, ikke et
    // array. Formen er en liste; værdien er tekst.
    const log = vis('git_log', {},
      JSON.stringify({ status: 'ok', log: 'abc123 fix(desk): x\ndef456 chore: y', n: 2 }))
    expect(log.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(log.container.textContent).toContain('abc123 fix(desk): x')
    expect(log.container.textContent).toContain('def456 chore: y')
    expect(log.container.querySelector('.rv-felter')).not.toBeInTheDocument()

    const st = vis('git_status', {},
      JSON.stringify({ status: 'ok', branch: 'main', changes: ' M a.ts\n?? b.ts' }))
    expect(st.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(st.container.textContent).toContain('M a.ts')
  })

  it('gør ikke en enkelt-linjes streng til en liste', () => {
    // Grænsen: én linje er et svar, ikke en liste. Ellers blev `{summary:"ok"}`
    // til en liste med ét punkt.
    const { container } = vis('git_status', {},
      JSON.stringify({ status: 'ok', branch: 'main', changes: '(clean)' }))
    expect(container.querySelector('.rv-liste')).not.toBeInTheDocument()
    expect(container.querySelector('.rv-felter')).toBeInTheDocument()
  })

  it('viser spørgsmål og billedmetadata uden IN/OUT-kort', () => {
    const ask = vis('pause_and_ask', { question: 'Fortsæt?' }, 'Ja')
    expect(ask.container.querySelector('.rv-sp')).toBeInTheDocument()
    expect(ask.container.textContent).toContain('Fortsæt?')
    ask.unmount()
    // Målt form: `analyze_image` sender `image_path` og svarer `{analysis}` —
    // ikke en rå dimensions-streng. Testen brugte den antagede form.
    const image = vis('analyze_image', { image_path: '/tmp/skaerm.png' },
      JSON.stringify({ analysis: 'Et skrivebord', model: 'deepseek-v4-flash', status: 'ok' }))
    expect(image.container.querySelector('.rv-bill')).toBeInTheDocument()
    expect(image.container.textContent).toContain('skaerm.png')
  })

  it('viser struktureret billedresultat som dimensioner og beskrivelse', () => {
    const { container } = vis('analyze_image', { path: 'photo.png' },
      JSON.stringify({ status: 'ok', result: { width: 1024, height: 768, description: 'Et skrivebord' } }))
    expect(container.textContent).toContain('1024 × 768')
    expect(container.textContent).toContain('Et skrivebord')
    expect(container.textContent).not.toContain('"width"')
  })

  it('viser analysens TEKST frem for «Image analyzed» (den målte form)', () => {
    // Målt på 161 faktiske kald: `analyze_image` svarer `{analysis, model,
    // status}` — ingen `width`, ingen `description`. Uden denne gren stod der
    // kun stien og «Image analyzed», altså METADATA om kaldet i stedet for det
    // kaldet fandt. Prompten vises som kontekst for hvad der blev spurgt om.
    const { container } = vis('analyze_image',
      { image_path: '/tmp/skaerm.png', prompt: 'Beskriv rækkevisningen' },
      JSON.stringify({ analysis: 'Rækkerne viser ikon og emne.', model: 'deepseek-v4-flash', status: 'ok' }))
    expect(container.querySelector('.rv-bill')).toBeInTheDocument()
    expect(container.textContent).toContain('Rækkerne viser ikon og emne.')
    expect(container.textContent).toContain('Beskriv rækkevisningen')
    expect(container.textContent).not.toContain('Image analyzed')
  })

  it('viser et ukendt struktureret resultat som nøgle-værdi frem for JSON', () => {
    const { container } = vis('some_new_tool', { path: 'a' },
      JSON.stringify({ status: 'ok', result: { count: 3, path: 'a', items: ['x', 'y'] } }))
    expect(container.textContent).toContain('count')
    expect(container.textContent).toContain('3')
    expect(container.querySelector('.rv-resultatH')?.textContent).not.toContain('"count"')
    expect(container.querySelector('details')).not.toHaveAttribute('open')
  })

  it('viser publicering som læsbare felter uden JSON-felt', () => {
    const { container } = vis('publish_file', { path: 'rapport.pdf' },
      JSON.stringify({ status: 'ok', url: 'https://example.org/rapport.pdf', size: 1234 }))
    expect(container.querySelector('.rv-resultatH')?.textContent).toContain('https://example.org/rapport.pdf')
    expect(container.querySelector('.rv-resultatH')?.textContent).not.toContain('"url"')
  })

  it('viser terminalens stdout og exit-kode uden JSON-skal', () => {
    const { container } = vis('operator_bash', { command: 'echo ok' },
      JSON.stringify({ result: { stdout: 'ok\n', exit_code: 0 } }))
    expect(container.querySelector('.rv-term pre')?.textContent).toBe('ok\n')
    expect(container.textContent).toContain('exit code 0')
  })

  it('viser kommandoen og en kørselsstatus straks, før stdout findes', () => {
    const { container } = render(<>{kropFor('operator_bash', {}, undefined, false, undefined,
      { partialJson: '{"command":"for i in 1 2; do sleep 1; done"', running: true })}</>)
    expect(container.querySelector('.rv-term .rv-kh')?.textContent).toContain('for i in 1 2; do sleep 1; done')
    expect(container.querySelector('.rv-term pre')?.textContent).toContain('Kører…')
    expect(container.textContent).not.toContain('exit code 0')
    expect(container.textContent).not.toContain('operator_bash')
  })

  it('opdaterer også en ufuldstændig kommando under streaming', () => {
    const { container } = render(<>{kropFor('operator_bash', {}, undefined, false, undefined,
      { partialJson: '{"command":"for i in 1 2; do sleep', running: true })}</>)
    expect(container.querySelector('.rv-term .rv-kh')?.textContent).toContain('for i in 1 2; do sleep')
  })

  it('beholder kommandoen når resultatet kommer, selv om input stadig er tomt', () => {
    const { container } = render(<>{kropFor('operator_bash', {},
      JSON.stringify({ result: { stdout: 'done', exit_code: 0 } }), false, undefined,
      { partialJson: '{"command":"echo done"}' })}</>)
    expect(container.querySelector('.rv-term .rv-kh')?.textContent).toContain('echo done')
    expect(container.querySelector('.rv-term pre')?.textContent).toBe('done')
    expect(container.textContent).toContain('exit code 0')
  })

  it('beholder terminalvisningen ved ikke-nul exit, når der er kommandooutput', () => {
    const { container } = vis('bash', { command: 'pytest' },
      JSON.stringify({ result: { stdout: '1 failed', exit_code: 1 } }), true)
    expect(container.querySelector('.rv-term')).toBeInTheDocument()
    expect(container.textContent).toContain('exit code 1')
    expect(container.textContent).toContain('1 failed')
  })

  it('viser ukendt værktøjs fejl først og lader rådata åbnes separat', () => {
    const { container } = vis('some_new_tool', { path: 'a' },
      JSON.stringify({ status: 'error', error: 'Adgang nægtet', debug: { code: 17 } }), true)
    expect(container.textContent).toContain('Adgang nægtet')
    expect(container.querySelector('details')).toBeInTheDocument()
    expect(container.querySelector('details')).not.toHaveAttribute('open')
  })

  it('viser en opgaveliste som linjer med status frem for JSON', () => {
    // `todo_set` gav 50 kald og `todo_update_status` 36 (23/9-2026) og faldt
    // til den generiske feltdump. Formen er linjer, ikke felter.
    const { container } = vis('todo_set', { todos: [] },
      JSON.stringify({ session_id: '_default', count: 3, todos: [
        { id: 'td-1', content: 'Rette navnekortet', status: 'completed' },
        { id: 'td-2', content: 'Bygge opgavelisten', status: 'in_progress' },
        { id: 'td-3', content: 'Skrive test', status: 'pending' },
      ] }))
    expect(container.querySelector('.rv-opgave')).toBeInTheDocument()
    expect(container.textContent).toContain('1 af 3')
    expect(container.textContent).toContain('1 i gang')
    expect(container.textContent).toContain('Bygge opgavelisten')
    expect(container.querySelector('[data-s="in_progress"]')).toBeInTheDocument()
    expect(container.textContent).not.toContain('"status"')
    expect(container.textContent).not.toContain('td-1')
  })

  it('viser også et enkelt opdateret punkt som opgaveliste', () => {
    const { container } = vis('todo_update_status', { todo_id: 'td-2', status: 'completed' },
      JSON.stringify({ status: 'ok', todo: { id: 'td-2', content: 'Bygge opgavelisten', status: 'completed' } }))
    expect(container.querySelector('.rv-opgave')).toBeInTheDocument()
    expect(container.textContent).toContain('Bygge opgavelisten')
    expect(container.textContent).toContain('1 af 1')
  })

  it('giver de mest brugte værktøjer en form — ingen falder til faldbacken', () => {
    // Vagt mod døde navne i navnekortet. Hvert navn her er målt i faktisk brug
    // (tool_usage, 23/9-2026) og SKAL have en form. Falder et af dem til 'fald',
    // er navnet enten stavet forkert eller slettet fra kortet — og så viser
    // rækkevisningen den generiske dump for et af de mest brugte værktøjer.
    const skalHaveForm = [
      'bash_session_run', 'operator_bash_session_run', 'bash_session_open',
      'operator_run_in_background', 'operator_bash_output', 'phone_adb_shell',
      'search', 'search_memory', 'search_sessions', 'search_jarvis_brain',
      'semantic_search_code', 'load_more_tools', 'recall', 'recall_memories',
      'git_log', 'git_status', 'git_diff', 'git_branch', 'eventbus_recent',
      'list_agents', 'list_self_wakeups', 'process_list', 'process_tail',
      'tail_log', 'central_query',
      'memory_upsert_section', 'send_telegram_message', 'notify_user',
      'operator_multi_edit', 'pause_and_ask', 'web_scrape', 'operator_webfetch',
      'operator_screenshot', 'look_around', 'read_visual_memory',
      'todo_set', 'todo_update_status', 'todo_add', 'todo_list',
    ]
    for (const navn of skalHaveForm) {
      expect(postFor(navn).familie, `${navn} mangler i navnekortet`).not.toBe('fald')
    }
  })

  it('mapper omdøbte værktøjer til deres nuværende form', () => {
    // Et omdøbt værktøj skal MAPPER, ikke slettes: gemte ture bærer det gamle
    // navn. `explore` → `scout_agent` (omdøbt 17/9-2026) er det vigtigste
    // tilfælde — uden opslaget faldt hver gammel spejder-tur til den generiske
    // dump, selv om underagent-rækken stod klar til at vise dens kald.
    //
    // Testen kræver ikke en bestemt familie: den kræver at gammelt og nyt
    // giver PRÆCIS samme form. Ændrer nogen det ene uden det andet, fejler den.
    const par: [string, string][] = [
      ['explore', 'scout_agent'],
      ['bash_session', 'bash_session_run'],
      ['operator_bash_session', 'operator_bash_session_run'],
      ['glob', 'operator_glob'],
      ['grep', 'operator_grep'],
      ['list_dir', 'operator_list_dir'],
      ['multi_edit', 'operator_multi_edit'],
      ['notify', 'notify_user'],
      ['memory_search', 'search_memory'],
      ['memory_write', 'memory_upsert_section'],
      ['search_files', 'search'],
    ]
    for (const [gammelt, nyt] of par) {
      expect(postFor(gammelt), `${gammelt} skal give samme form som ${nyt}`)
        .toEqual(postFor(nyt))
    }
  })

  it('farver terminal-udskrift efter ANSI-koderne i stedet for at vise dem raat', () => {
    // `ls --color`, `git diff --color` og `grep --color` skriver SGR-koder ind
    // i stdout. Foer stod `\x1b[32m` som skrald midt i teksten.
    const raa = JSON.stringify({ result: { stdout: '\x1b[32mOK\x1b[0m fejl \x1b[31mNEJ\x1b[0m', exit_code: 0 } })
    const { container } = vis('operator_bash', { command: 'ls --color' }, raa)
    expect(container.querySelector('.rv-ansi-2')?.textContent).toBe('OK')
    expect(container.querySelector('.rv-ansi-1')?.textContent).toBe('NEJ')
    expect(container.textContent).not.toContain('\x1b')
    expect(container.textContent).toContain('fejl')
  })

  it('genkender sproget fra filnavnet naar endelsen ikke siger noget', () => {
    // `Dockerfile`, `Makefile` og `.env` har ingen brugbar endelse og faldt
    // til `text`, altsaa ingen farve.
    const { container } = vis('read_file', { path: '/srv/app/Dockerfile' },
      JSON.stringify({ status: 'ok', result: 'FROM node:22\nRUN npm ci' }))
    expect(container.querySelector('.rv-filKode')).toHaveAttribute('data-lang', 'dockerfile')
  })

  it('farver koden i en redigering naar stien kendes', async () => {
    const { container } = vis('operator_edit_file', { path: 'app.ts', old_string: 'const a = 1', new_string: 'const a = 2' },
      JSON.stringify({ status: 'ok', result: { replacements: 1 } }))
    await waitFor(() => expect(container.querySelector('.rv-diff .shiki .line')).toBeInTheDocument(), { timeout: 5000 })
    expect(container.querySelector('.rv-diff')).toHaveAttribute('data-lang', 'typescript')
    expect(container.querySelector('.rv-diff .shiki .line[data-k="del"]')).toBeInTheDocument()
    expect(container.querySelector('.rv-diff .shiki .line[data-k="add"]')).toBeInTheDocument()
  })

  it('bygger redigeringens diff af multi_edit-parrene frem for at dumpe metadata', () => {
    // Kroppen ledte efter `old_string` på topniveau og krævede desuden
    // `status === 'ok'`. `operator_multi_edit` bærer parrene i `edits[]` og
    // sender ingen status — så rækken viste `replacements`, `edits`, `path`
    // og `strategies` i stedet for ændringen. Bjørn 23/9-2026: «det er jo ikk
    // info jeg kan bruge til noget».
    const { container } = vis('operator_multi_edit', {
      path: '/srv/app.ts',
      edits: [{ old_text: 'const a = 1', new_text: 'const a = 2' }],
    }, JSON.stringify({ result: { replacements: 1, edits: 1, path: '/srv/app.ts', strategies: ['exact'] } }))
    expect(container.querySelector('.rv-diff')).toBeInTheDocument()
    expect(container.querySelector('[data-k="del"]')?.textContent).toContain('const a = 1')
    expect(container.querySelector('[data-k="add"]')?.textContent).toContain('const a = 2')
    // Faldbacken ville tegne `.rv-resultat` med feltlisten i stedet.
    expect(container.querySelector('.rv-resultat')).not.toBeInTheDocument()
  })

  it('viser den faktiske besked når et kald afvises uden struktur', () => {
    // Read-guarden svarer med ren tekst, ikke JSON. `fejlTekst` leder efter et
    // `error`-felt og fandt intet, så rækken stod med «The tool could not
    // complete» — mens forklaringen lå ulæst inde i Raw data.
    const { container } = vis('operator_edit_file', { path: '/srv/app.ts', old_text: 'a', new_text: 'b' },
      '⚠️ READ-BEFORE-WRITE GUARD (operator): /srv/app.ts skal læses først i denne session.', true)
    const hoved = container.querySelector('.rv-resultatH')
    expect(hoved?.textContent).toContain('READ-BEFORE-WRITE GUARD')
    expect(hoved?.textContent).not.toContain('The tool could not complete')
  })

  it('viser filens indhold når den er skrevet, også uden status i resultatet', () => {
    const { container } = vis('operator_write_file', { path: '/srv/notes.md', content: '# Noter\n- et punkt' },
      JSON.stringify({ result: { bytes_written: 17, path: '/srv/notes.md' } }))
    expect(container.querySelector('.rv-fil')).toBeInTheDocument()
    expect(container.textContent).toContain('et punkt')
  })

  it('viser mindet der blev skrevet frem for id-et det fik', () => {
    // `remember_this` svarer med `{id}` — UDEN `status`. Den oprindelige test
    // brugte `{status: 'ok', id}`, altså den form jeg TROEDE på, og pinnede
    // dermed sin egen fantasi: grenen krævede `bekræftet()`, som sagde nej
    // til `{id}`, og rækken faldt til feltlisten og viste «id brn_…». Målt på
    // 24 faktiske kald 23/9-2026: alle bar præcis `{id}`.
    const { container } = vis('remember_this', {
      kind: 'indsigt', title: 'Byg-rækkefølgen',
      content: 'Kode committet efter build er ikke i appen.',
      visibility: 'personal', domain: 'projects',
    }, JSON.stringify({ id: 'brn_01M37WQ4JF2XH3KQX1HNJ4SD6E' }))
    expect(container.querySelector('.rv-minde')).toBeInTheDocument()
    expect(container.textContent).toContain('Byg-rækkefølgen')
    expect(container.textContent).toContain('Kode committet efter build')
    expect(container.textContent).toContain('indsigt')
    expect(container.textContent).not.toContain('brn_01M37WQ4')
  })

  it('viser MEMORY.md-sektionen der blev skrevet', () => {
    const { container } = vis('memory_upsert_section', { heading: 'Beslutninger', content: '- vi bygger videre' },
      "MEMORY.md section 'Beslutninger' added successfully.")
    expect(container.querySelector('.rv-minde')).toBeInTheDocument()
    expect(container.textContent).toContain('Beslutninger')
    expect(container.textContent).toContain('vi bygger videre')
  })

  it('viser ikke et minde der IKKE blev gemt', () => {
    // Et fejlet kald må ikke vise teksten som om den var skrevet.
    const { container } = vis('remember_this', { kind: 'indsigt', title: 'T', content: 'C' },
      JSON.stringify({ status: 'error', error: 'rate_limit_turn' }))
    expect(container.querySelector('.rv-minde')).not.toBeInTheDocument()
  })

  it('lader publish_file beholde sin feltliste', () => {
    // Den bærer også `content`, men skriver ikke en fil. Uden sti-kravet ville
    // dens tekst blive dumpet som et filkort.
    const a = vis('publish_file', { filename: 'x.csv', content: 'a,b' }, JSON.stringify({ url: 'http://x' }))
    expect(a.container.querySelector('.rv-fil')).not.toBeInTheDocument()
    // Et minde er heller ikke et filkort — det har sin egen form.
    const b = vis('memory_upsert_section', { heading: 'H', content: 'tekst' },
      "MEMORY.md section 'H' added successfully.")
    expect(b.container.querySelector('.rv-fil')).not.toBeInTheDocument()
    expect(b.container.querySelector('.rv-minde')).toBeInTheDocument()
  })

  it('udleder formen af resultatet naar navnet ikke staar i navnekortet', () => {
    // Maalt 23/9-2026 over 35.027 parrede kald: 71 vaerktoejer havde slet
    // ingen form — 372 af 472 kald — fordi navnekortet er manuelt
    // vedligeholdt. Familien foelger RESULTATETS form, saa den kan udledes.
    // `goal_list` bar `{count, goals:[…]}`:
    const mål = vis('goal_list', {}, JSON.stringify({ count: 10, goals: [
      { goal_id: 'goal_ed7b', title: 'Laer at holde tillid', priority: 70 },
      { goal_id: 'goal_11aa', title: 'Byg videre', priority: 50 },
    ], stats: { active: 2 } }))
    expect(mål.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(mål.container.textContent).toContain('Laer at holde tillid')
    // `jarvis_browser_tabs` pakker listen ET niveau ned — `{result:{tabs}}`:
    const faner = vis('jarvis_browser_tabs', {}, JSON.stringify({ result: { tabs: [
      { id: 1, url: 'https://jarvis.srvlab.dk/', titel: 'J.A.R.V.I.S.' },
    ] } }))
    expect(faner.container.querySelector('.rv-liste')).toBeInTheDocument()
    expect(faner.container.textContent).toContain('J.A.R.V.I.S.')
  })

  it('viser indholdet naar resultatet ligger i én noegle — ikke optaellingen', () => {
    // `schedule_self_wakeup` svarer `{wakeup:{…}}`. Uden udpakningen stod der
    // «wakeup | 6 fields» — en optaelling i stedet for de seks felter.
    const v = vis('schedule_self_wakeup', { delay_seconds: 600 },
      JSON.stringify({ wakeup: { wakeup_id: 'wake-d53e8bd0ca', fire_at: '2026-09-23T14:45:48Z', reason: 'check-build' } }))
    expect(v.container.textContent).toContain('check-build')
    expect(v.container.textContent).not.toContain('3 fields')
    // `set_flag` svarer `{confirmed, flag:{…}}` — boolean ved siden af:
    const f = vis('set_flag', { key: 'dream_carry_over' },
      JSON.stringify({ confirmed: true, flag: { key: 'dream_carry_over', ttl_minutes: 30 } }))
    expect(f.container.textContent).toContain('dream_carry_over')
    expect(f.container.textContent).toContain('30')
  })

  it('lader et fladt status-objekt beholde sin feltliste', () => {
    // Det ER dens form: `get_weather` bærer temp_c/humidity_pct som flade
    // felter. At tvinge den ind i en anden familie ville goere formen
    // ringere, ikke bedre — udledningen maa ikke ramme den.
    const { container } = vis('get_weather', { city: 'Svendborg' },
      JSON.stringify({ city: 'Svendborg, DK', temp_c: 11.84, humidity_pct: 88 }))
    expect(container.querySelector('.rv-felter')).toBeInTheDocument()
    expect(container.textContent).toContain('11.84')
  })

  it('viser indholdet i en liste i stedet for at taelle den', () => {
    // Maalt 23/9-2026: 242 kald (10 %, 51 vaerktoejer) skrev «2 items» eller
    // «4 fields» i stedet for indholdet. `restart_self` skjulte hvilke
    // services den genstarter.
    const { container } = vis('restart_self', {},
      JSON.stringify({ scheduled: true, services: ['jarvis-api', 'jarvis-runtime'], delay_seconds: 3 }))
    expect(container.textContent).toContain('jarvis-api')
    expect(container.textContent).toContain('jarvis-runtime')
    expect(container.textContent).not.toContain('2 items')
  })

  it('viser flagets felter naar resultatet ligger i én noegle', () => {
    // `set_flag` svarer `{confirmed, flag:{…}}`. Uden udpakningen stod der
    // «flag | 4 fields» — flagets navn og levetid laa i argumenterne og i
    // det indre objekt, og ingen af dem blev vist.
    const { container } = vis('set_flag', { key: 'dream_carry_over' },
      JSON.stringify({ confirmed: true, flag: { key: 'dream_carry_over', ttl_minutes: 30 } }))
    expect(container.textContent).toContain('ttl_minutes')
    expect(container.textContent).toContain('30')
    expect(container.textContent).not.toContain('fields')
  })
})

describe('billedet kan ses — ogsaa naar filen ligger paa serveren', () => {
  const CONFIG: ApiConfig = { apiBaseUrl: 'http://server', authToken: 'tok' }

  // jsdom har hverken `createObjectURL` eller en server. Begge stubbes, saa
  // testen maaler KOMPONENTEN og ikke miljoeet.
  beforeEach(() => {
    ;(URL as unknown as { createObjectURL: unknown }).createObjectURL = vi.fn(() => 'blob:hentet')
    ;(URL as unknown as { revokeObjectURL: unknown }).revokeObjectURL = vi.fn()
  })
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('henter billedet fra serveren naar det ikke findes lokalt', async () => {
    // Jarvis' skaermbilleder ligger i temp-mappen paa SERVEREN, saa broen
    // svarer null hos brugeren. Uden server-sporet stod navnet alene, og man
    // kunne ikke se det samme som Jarvis (24/9-2026).
    const hentet = vi.fn(async (_url: string) => new Response(new Blob([new Uint8Array([1, 2, 3])]), { status: 200 }))
    vi.stubGlobal('fetch', hentet)

    const { container } = vis('analyze_image',
      { image_path: '/tmp/jarvisx-window-1.png', prompt: 'Hvad ser du?' },
      JSON.stringify({ analysis: 'Et skrivebord' }), false, CONFIG)

    await waitFor(() => expect(container.querySelector('.billed-knap')).toBeInTheDocument())
    const url = String(hentet.mock.calls[0]?.[0] ?? '')
    expect(url).toContain('/visning/billede')
    expect(url).toContain(encodeURIComponent('/tmp/jarvisx-window-1.png'))
    // Analysens tekst er stadig INDHOLDET — den staar ved siden af billedet.
    expect(container.textContent).toContain('Et skrivebord')
  })

  it('aabner billedet i fuld stoerrelse ved klik', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(new Blob([new Uint8Array([1])]), { status: 200 })))
    const { container } = vis('analyze_image',
      { image_path: '/tmp/jarvisx-window-2.png' },
      JSON.stringify({ analysis: 'Et skrivebord' }), false, CONFIG)

    await waitFor(() => expect(container.querySelector('.billed-knap')).toBeInTheDocument())
    expect(container.querySelector('.billed-lightbox')).not.toBeInTheDocument()
    fireEvent.click(container.querySelector('.billed-knap') as HTMLButtonElement)
    await waitFor(() => expect(container.querySelector('.billed-lightbox')).toBeInTheDocument())
  })

  it('viser navnet naar billedet hverken findes lokalt eller paa serveren', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('nej', { status: 404 })))
    const { container } = vis('analyze_image',
      { image_path: '/tmp/jarvisx-window-3.png' },
      JSON.stringify({ analysis: 'Et skrivebord' }), false, CONFIG)

    await waitFor(() => expect(container.textContent).toContain('Et skrivebord'))
    expect(container.querySelector('.billed-knap')).not.toBeInTheDocument()
    expect(container.textContent).toContain('jarvisx-window-3.png')
  })
})
