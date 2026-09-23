import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { kropFor, postFor, udDel, exitKode } from './raekkeKroppe'

function vis(navn: string, input: Record<string, unknown>, result?: string, fejl = false) {
  return render(<>{kropFor(navn, input, result, fejl)}</>)
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

  it('viser spørgsmål og billedmetadata uden IN/OUT-kort', () => {
    const ask = vis('pause_and_ask', { question: 'Fortsæt?' }, 'Ja')
    expect(ask.container.querySelector('.rv-sp')).toBeInTheDocument()
    expect(ask.container.textContent).toContain('Fortsæt?')
    ask.unmount()
    const image = vis('analyze_image', { path: 'photo.png' }, '1024 × 768')
    expect(image.container.querySelector('.rv-bill')).toBeInTheDocument()
    expect(image.container.textContent).toContain('photo.png')
  })

  it('viser struktureret billedresultat som dimensioner og beskrivelse', () => {
    const { container } = vis('analyze_image', { path: 'photo.png' },
      JSON.stringify({ status: 'ok', result: { width: 1024, height: 768, description: 'Et skrivebord' } }))
    expect(container.textContent).toContain('1024 × 768')
    expect(container.textContent).toContain('Et skrivebord')
    expect(container.textContent).not.toContain('"width"')
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
      'git_log', 'eventbus_recent', 'list_agents', 'list_self_wakeups',
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

  it('lader publish_file og memory_upsert_section beholde deres feltliste', () => {
    // De bærer også `content`, men skriver ikke en fil. Uden sti-kravet ville
    // deres tekst blive dumpet som et filkort.
    const a = vis('publish_file', { filename: 'x.csv', content: 'a,b' }, JSON.stringify({ url: 'http://x' }))
    expect(a.container.querySelector('.rv-fil')).not.toBeInTheDocument()
    const b = vis('memory_upsert_section', { heading: 'H', content: 'tekst' }, JSON.stringify({ ok: true }))
    expect(b.container.querySelector('.rv-fil')).not.toBeInTheDocument()
  })
})
