import { readdirSync, readFileSync } from 'fs'
import { join } from 'path'
import {
  kropFor, kropForResult, kanTegneKrop, formFamilie, foersteListe, listeTekst,
  listePoster, tekstLinjer, udenHale, pakUd, udDel, exitKode, filTekst, filnavn,
  LISTE_NAVNE,
  mindeIndhold, webTraef, spoergsmaalIndhold, billedeIndhold, opgavePoster,
  agentIdFra, erFejl, fejlBesked, skrivBesked,
} from './krop'

describe('kropFor', () => {
  it('bash-familien er terminal — også de session-baserede', () => {
    for (const n of ['bash', 'operator_bash', 'bash_session_run', 'operator_run_in_background', 'phone_adb_shell']) {
      expect(kropFor(n)).toBe('terminal')
    }
  })

  it('fil-læsning er fil — begge stavemåder', () => {
    expect(kropFor('read_file')).toBe('fil')
    expect(kropFor('operator_read_file')).toBe('fil')
  })

  it('skrivning og redigering er diff', () => {
    for (const n of ['edit_file', 'operator_multi_edit', 'write_file', 'operator_write_file']) {
      expect(kropFor(n)).toBe('diff')
    }
  })

  it('soegning, git og oversigter er liste — hitlister og tabeller', () => {
    for (const n of ['search', 'find_files', 'git_status', 'list_self_wakeups', 'central_query']) {
      expect(kropFor(n)).toBe('liste')
    }
  })

  it('alt andet falder til den rå form — det er ikke en fejl', () => {
    // Små status-objekter (`daemon_status`, `get_weather`) ER feltlisten.
    // En ukendt form maa ikke gættes; den skal falde tilbage.
    expect(kropFor('daemon_status')).toBe('fald')
    expect(kropFor('findes_ikke_som_vaerktoej')).toBe('fald')
  })
})

describe('udenHale', () => {
  it('fjerner serverens interne instruks fra resultatet', () => {
    const med = '{"exit_code": 0}\n\n(⟳ Fortsaet: skriv en kort saetning.)'
    expect(udenHale(med)).toBe('{"exit_code": 0}')
  })

  it('roerer ikke et resultat uden hale', () => {
    expect(udenHale('hej')).toBe('hej')
  })
})

describe('pakUd', () => {
  it('pakker indpakkede result-skaller ud', () => {
    // Serveren lægger nogle gange resultatet i et objekt under `result`.
    const r = pakUd('{"result": {"exit_code": 3}}')
    expect(r.vaerdi).toEqual({ exit_code: 3 })
    expect(r.ramme).toEqual({ result: { exit_code: 3 } })
  })

  it('raa tekst uden JSON giver strengen selv og ingen ramme', () => {
    const r = pakUd('bare tekst')
    expect(r.vaerdi).toBe('bare tekst')
    expect(r.ramme).toBeNull()
  })

  it('tomt resultat giver tom streng', () => {
    expect(pakUd(undefined).vaerdi).toBe('')
  })
})

describe('udDel', () => {
  it('tager stdout og stderr — ikke hele JSON-blobben', () => {
    const r = '{"stdout": "fil1\\nfil2", "stderr": "advarsel", "exit_code": 0}'
    expect(udDel(r)).toBe('fil1\nfil2\nadvarsel')
  })

  it('falder tilbage til hele teksten naar der intet stdout er', () => {
    expect(udDel('ren tekst')).toBe('ren tekst')
  })

  it('tomt resultat giver tom streng', () => {
    expect(udDel(undefined)).toBe('')
  })
})

describe('exitKode', () => {
  it('laeser exit_code fra JSON', () => {
    expect(exitKode('{"exit_code": 7}', false)).toBe(7)
  })

  it('laeser ogsaa returncode og den indpakkede form', () => {
    expect(exitKode('{"returncode": 2}', false)).toBe(2)
    expect(exitKode('{"result": {"exit_code": 5}}', false)).toBe(5)
  })

  it('laeser tekstmaerket naar resultatet ikke er JSON', () => {
    expect(exitKode('noget output\n[exit code: 4]', false)).toBe(4)
  })

  it('falder tilbage paa fejlflaget — ikke paa et gæt', () => {
    expect(exitKode('ingen kode her', true)).toBe(1)
    expect(exitKode('ingen kode her', false)).toBe(0)
    expect(exitKode(undefined, false)).toBe(0)
  })
})

describe('filTekst', () => {
  it('tager content-feltet naar filen er pakket i JSON', () => {
    expect(filTekst('{"content": "linje 1\\nlinje 2"}')).toBe('linje 1\nlinje 2')
  })

  it('tager raa tekst naar filen ikke er pakket', () => {
    expect(filTekst('linje 1\nlinje 2')).toBe('linje 1\nlinje 2')
  })

  it('tomt resultat giver tom streng', () => {
    expect(filTekst(undefined)).toBe('')
  })
})

describe('filnavn', () => {
  it('giver sidste led af stien', () => {
    expect(filnavn('/media/projects/jarvis-v2/apps/mobile/src/lib/krop.ts')).toBe('krop.ts')
  })

  it('haandterer windows-stier', () => {
    expect(filnavn('C:\\Users\\bs\\note.txt')).toBe('note.txt')
  })
})

describe('foersteListe', () => {
  it('finder listen uanset hvad noeglen hedder', () => {
    // De fire navne huset faktisk bruger: `results` (soegning), `files`
    // (find_files), `wakeups` (list_self_wakeups) og `matches`.
    expect(foersteListe({ status: 'ok', results: [{ a: 1 }] })).toEqual([{ a: 1 }])
    expect(foersteListe({ files: ['a.ts'] })).toEqual(['a.ts'])
    expect(foersteListe({ wakeups: [{ id: 1 }] })).toEqual([{ id: 1 }])
    expect(foersteListe({ matches: [{ line: 2 }] })).toEqual([{ line: 2 }])
  })

  it('graver ét niveau ned — central_query pakker i `data`', () => {
    expect(foersteListe({ data: { items: [{ id: 'x' }] } })).toEqual([{ id: 'x' }])
  })

  it('en tom liste er ingen liste', () => {
    expect(foersteListe({ results: [] })).toBeNull()
    expect(foersteListe({ status: 'ok' })).toBeNull()
    expect(foersteListe('ren tekst')).toBeNull()
  })

  it('graver ikke vilkaarligt dybt — ellers blev enhver struktur en liste', () => {
    expect(foersteListe({ a: { b: { c: [1] } } })).toBeNull()
  })
})

describe('listeTekst', () => {
  it('tager de kendte felter foerst', () => {
    expect(listeTekst({ text: 'linjen', name: 'noget' })).toBe('linjen')
    expect(listeTekst({ path: 'a.ts', line: 3 })).toBe('a.ts')
    expect(listeTekst({ content: 'brødtekst' })).toBe('brødtekst')
  })

  it('et punkt uden kendte felter viser SINE felter — ikke ordet «Result»', () => {
    // `list_self_wakeups` bærer `prompt`, `central_query` bærer `id`/`kind`.
    expect(listeTekst({ id: 'w1', kind: 'fakta' })).toBe('id=w1 · kind=fakta')
  })

  it('klipper et langt punkt — et punkt er et punkt, ikke et dokument', () => {
    const lang = 'x'.repeat(500)
    const ud = listeTekst({ text: lang })
    expect(ud.length).toBeLessThan(320)
    expect(ud.endsWith('…')).toBe(true)
  })

  it('en ren streng vises som den er', () => {
    expect(listeTekst('bare en sti')).toBe('bare en sti')
  })
})

describe('tekstLinjer', () => {
  it('en streng med flere linjer ER en liste — git log og git status', () => {
    expect(tekstLinjer({ log: 'abc123 forrige\nfed456 nyeste' })).toEqual(['abc123 forrige', 'fed456 nyeste'])
  })

  it('én linje er ikke en liste — et enkelt svar maa ikke blive et punkt', () => {
    expect(tekstLinjer({ summary: 'ok' })).toBeNull()
  })

  it('springer status over og tomme linjer over', () => {
    expect(tekstLinjer({ status: 'ok\nfejl', changes: 'M a.ts\n\nM b.ts' })).toEqual(['M a.ts', 'M b.ts'])
  })
})

describe('listePoster', () => {
  it('saetter sti og linjetal foran punktet', () => {
    const r = '{"results":[{"file":"a.ts","line":42,"text":"const x = 1"}]}'
    expect(listePoster(r)).toEqual([{ p: 'a.ts:42', v: 'const x = 1' }])
  })

  it('et punkt uden sti faar intet praefiks', () => {
    expect(listePoster('{"files":["a.ts","b.ts"]}')).toEqual([{ v: 'a.ts' }, { v: 'b.ts' }])
  })

  it('falder til tekst-linjer naar der ikke er et array', () => {
    expect(listePoster('{"changes":"M a.ts\\nM b.ts"}')).toEqual([{ v: 'M a.ts' }, { v: 'M b.ts' }])
  })

  it('giver null naar der hverken er liste eller linjer — saa tegnes INTET', () => {
    // Det er denne vej der goer at kaldsstedet kan falde til raa tekst i
    // stedet for at vise en tom ramme.
    expect(listePoster('ren tekst uden struktur')).toBeNull()
    expect(listePoster(undefined)).toBeNull()
  })
})

describe('formFamilie', () => {
  it('en liste ER en liste — uanset hvilket vaerktoej der sendte den', () => {
    expect(formFamilie('{"results":[{"a":1}]}')).toBe('liste')
    expect(formFamilie('{"goals":[{"a":1}]}')).toBe('liste')
  })

  it('en optaelling ved siden af listen er stadig en liste', () => {
    expect(formFamilie('{"count":2,"goals":[{"a":1}]}')).toBe('liste')
  })

  it('staar der meningsfulde felter VED SIDEN AF, er objektet formen', () => {
    // `{count, path, items:[…]}` — `path` er indhold, ikke en optaelling.
    expect(formFamilie('{"count":2,"path":"/x","items":[{"a":1}]}')).toBe('fald')
  })

  it('stdout eller stderr goer resultatet til en terminal', () => {
    expect(formFamilie('{"status":"ok","stdout":"hej"}')).toBe('terminal')
  })

  it('et fladt status-objekt forbliver den raa form — det ER dens form', () => {
    // `get_weather`, `set_flag`: en gættet form ville være ringere end ingen.
    expect(formFamilie('{"status":"ok","temp":14.6}')).toBe('fald')
    expect(formFamilie('ren tekst')).toBe('fald')
  })
})

describe('kropForResult', () => {
  it('navnet vinder naar det staar i en tabel', () => {
    expect(kropForResult('search', '{"results":[{"a":1}]}')).toBe('liste')
    expect(kropForResult('bash', '{"stdout":"x"}')).toBe('terminal')
  })

  it('navnet vinder ogsaa naar formen ville sige noget andet', () => {
    // DEN VIGTIGE: `search_chat_history` svarer med `text` VED SIDEN AF listen,
    // saa form-reglen alene ville give `fald`. Navnet er den viden resultatet
    // ikke bærer.
    const r = '{"status":"ok","count":1,"results":[{"role":"user"}],"text":"Found 1"}'
    expect(formFamilie(r)).toBe('fald')
    expect(kropForResult('search_chat_history', r)).toBe('liste')
  })

  it('RAEKKEFOELGEN maales: et kendt navn slaar en liste-form', () => {
    // Vagt mod at bytte om på de to lag. `bash` er terminal, og selv om
    // resultatet bærer en liste, er det stadig en terminal — navnet er den
    // viden formen ikke har. Uden denne test slap ombytningen igennem
    // mutationsproeven, fordi `search_chat_history`-tilfældet giver `liste`
    // ad BEGGE veje og derfor ikke maaler rækkefølgen.
    expect(formFamilie('{"results":[{"a":1}]}')).toBe('liste')
    expect(kropForResult('bash', '{"results":[{"a":1}]}')).toBe('terminal')
  })

  it('formen fanger de vaerktoejer ingen tabel har', () => {
    expect(kropForResult('list_events', '{"events":[{"titel":"moede"}]}')).toBe('liste')
    expect(kropForResult('et_ukendt_vaerktoej', '{"status":"ok"}')).toBe('fald')
  })
})

describe('kanTegneKrop', () => {
  it('en liste-familie med ren tekst kan IKKE tegnes — saa falder vi til raa tekst', () => {
    // Uden dette lovede kaldsstedet en krop og tegnede en TOM ramme.
    expect(kanTegneKrop('liste', 'ren tekst')).toBe(false)
    expect(kanTegneKrop('liste', '{"results":[{"a":1}]}')).toBe(true)
  })

  it('terminal og fil kraever ogsaa indhold', () => {
    expect(kanTegneKrop('terminal', '{"stdout":"hej"}')).toBe(true)
    // Et bash-kald UDEN stdout viser sin rå JSON: `udDel` falder tilbage til
    // hele teksten, og det er stadig noget at vise — samme tekst som den rå vej
    // ville give. Kun et HELT tomt resultat tegnes ikke.
    expect(kanTegneKrop('terminal', '{"exit_code":0}')).toBe(true)
    expect(kanTegneKrop('terminal', '')).toBe(false)
    expect(kanTegneKrop('fil', '')).toBe(false)
    expect(kanTegneKrop('fil', 'linje 1')).toBe(true)
  })

  it('den raa form tegnes aldrig som krop', () => {
    expect(kanTegneKrop('fald', '{"status":"ok"}')).toBe(false)
  })
})

describe('navnene findes i registret', () => {
  it('hvert liste-navn staar i serverens vaerktoejskilde', () => {
    // Kilden til sandheden er `core/tools/` — 485 værktøjer, defineret i Python.
    // Vi læser den som TEKST. Et navn der ikke findes nogen steder kan ikke
    // kaldes, og en form for et navn der ikke findes LYVER hvis navnet en dag
    // bruges til noget andet. Desk havde otte sådanne (målt 23/9-2026), og
    // deres egen kommentar pegede på en vagt-test der ikke fandtes.
    const rod = join(__dirname, '..', '..', '..', '..')
    const mappe = join(rod, 'core', 'tools')
    const kilde = readdirSync(mappe)
      .filter((f) => f.endsWith('.py'))
      .map((f) => readFileSync(join(mappe, f), 'utf8'))
      .join('\n')
    const mangler = LISTE_NAVNE.filter((n) => !kilde.includes(`"${n}"`))
    expect(mangler).toEqual([])
  })
})

describe('kropFor — de ni nye familier', () => {
  it('skriv-vaerktoejerne er skriv', () => {
    for (const n of ['publish_file', 'notify_user', 'verify_file_contains']) {
      expect(kropFor(n)).toBe('skriv')
    }
  })

  it('de to minde-skrivninger er minde — ikke skriv', () => {
    // Indholdet staar i argumenterne, og kroppen skal vise det.
    expect(kropFor('remember_this')).toBe('minde')
    expect(kropFor('memory_upsert_section')).toBe('minde')
  })

  it('web-vaerktoejerne er web', () => {
    for (const n of ['web_search', 'web_fetch', 'operator_webfetch', 'web_scrape']) {
      expect(kropFor(n)).toBe('web')
    }
  })

  it('pause_and_ask er spoergsmaal', () => {
    expect(kropFor('pause_and_ask')).toBe('spoergsmaal')
  })

  it('billed-vaerktoejerne er billede', () => {
    for (const n of ['analyze_image', 'operator_screenshot', 'operator_screenshot_window', 'look_around', 'read_visual_memory']) {
      expect(kropFor(n)).toBe('billede')
    }
  })

  it('todo-vaerktoejerne er opgave', () => {
    for (const n of ['todo_set', 'todo_add', 'todo_update_status', 'todo_remove', 'todo_list']) {
      expect(kropFor(n)).toBe('opgave')
    }
  })

  it('scout_agent er underagent — ikke skriv', () => {
    expect(kropFor('scout_agent')).toBe('underagent')
  })
})

describe('mindeIndhold', () => {
  it('laeser titel og tekst af ARGUMENTERNE', () => {
    // `remember_this` svarer kun `{id}` — indholdet findes ikke i resultatet.
    const m = mindeIndhold(JSON.stringify({ title: 'Fundet', content: 'En linje', kind: 'fakta', domain: 'self' }))
    expect(m).toEqual({ titel: 'Fundet', meta: 'fakta · self', tekst: 'En linje' })
  })

  it('tager ogsaa imod et objekt og et heading-felt', () => {
    expect(mindeIndhold({ heading: 'H', text: 'T' })).toEqual({ titel: 'H', meta: '', tekst: 'T' })
  })

  it('giver null naar titel eller tekst mangler', () => {
    expect(mindeIndhold('{"title":"x"}')).toBeNull()
    expect(mindeIndhold('ikke json')).toBeNull()
    expect(mindeIndhold(undefined)).toBeNull()
  })
})

describe('webTraef', () => {
  it('tager traef-listen med domaene og titel', () => {
    const t = webTraef('{"results":[{"url":"https://a.dk","title":"A"}]}')
    expect(t).toEqual([{ dom: 'https://a.dk', titel: 'A' }])
  })

  it('afviser en liste UDEN url — den er ikke et web-resultat', () => {
    // Uden det krav ville enhver liste af objekter blive laest som en soegning.
    expect(webTraef('{"results":[{"text":"noget"}]}')).toBeNull()
    expect(webTraef('{}')).toBeNull()
  })
})

describe('spoergsmaalIndhold', () => {
  it('spoergsmaalet fra argumenterne, svaret fra resultatet', () => {
    const s = spoergsmaalIndhold('{"question":"Hvilken?"}', '{"answer":"Den anden"}')
    expect(s).toEqual({ q: 'Hvilken?', svar: 'Den anden' })
  })

  it('giver null naar begge sider er tomme', () => {
    expect(spoergsmaalIndhold('{}', '{}')).toBeNull()
  })
})

describe('opgavePoster', () => {
  it('laeser todos-listen med status', () => {
    const p = opgavePoster('{"count":2,"todos":[{"content":"a","status":"completed"},{"content":"b","status":"in_progress"}]}')
    expect(p).toEqual([{ tekst: 'a', status: 'completed' }, { tekst: 'b', status: 'in_progress' }])
  })

  it('laeser den ENKELTE todo fra todo_update_status', () => {
    expect(opgavePoster('{"todo":{"content":"a","status":"pending"}}')).toEqual([{ tekst: 'a', status: 'pending' }])
  })

  it('giver null naar der ingen liste er', () => {
    expect(opgavePoster('{"status":"ok"}')).toBeNull()
  })
})

describe('agentIdFra', () => {
  it('laeser agent_id — og giver null uden', () => {
    expect(agentIdFra('{"agent_id":"ag-1"}')).toBe('ag-1')
    expect(agentIdFra('{"status":"ok"}')).toBeNull()
  })
})

describe('erFejl', () => {
  it('fanger de fire afviste statusser', () => {
    for (const st of ['error', 'blocked', 'approval_needed', 'guard_blocked']) {
      expect(erFejl(JSON.stringify({ status: st }))).toBe(true)
    }
  })

  it('et normalt resultat er ikke en fejl', () => {
    expect(erFejl('{"status":"ok","stdout":"hej"}')).toBe(false)
    expect(erFejl('ren tekst')).toBe(false)
  })
})

describe('fejlBesked', () => {
  it('tager fejl-feltet naar det findes', () => {
    expect(fejlBesked('{"error":"Stien maa ikke vises"}')).toBe('Stien maa ikke vises')
  })

  it('springer et JSON-dokument over og tager foerste meningsfulde linje', () => {
    // En afvist bro-handling er ren TEKST. Foerste linje ville vaere `{`.
    expect(fejlBesked('{"a":1}\nNej, det maa du ikke')).toBe('Nej, det maa du ikke')
  })
})

describe('formFamilie — web og opgave FOER liste', () => {
  it('en traef-liste er web, ikke liste', () => {
    expect(formFamilie('{"results":[{"url":"https://a.dk","title":"A"}]}')).toBe('web')
  })

  it('en todo-liste er opgave, ikke liste', () => {
    expect(formFamilie('{"todos":[{"content":"a","status":"pending"}]}')).toBe('opgave')
  })
})

describe('kropForResult — fejl gaar FOER navnet', () => {
  it('et afvist bash-kald er fejl, ikke terminal', () => {
    expect(kropForResult('bash', '{"status":"approval_needed","stdout":""}')).toBe('fejl')
  })

  it('et normalt bash-kald er stadig terminal', () => {
    expect(kropForResult('bash', '{"status":"ok","stdout":"hej"}')).toBe('terminal')
  })
})

describe('kanTegneKrop — de nye', () => {
  it('minde kraever argumenterne, ikke resultatet', () => {
    expect(kanTegneKrop('minde', '{"id":"x"}', '{"title":"t","content":"c"}')).toBe(true)
    expect(kanTegneKrop('minde', '{"id":"x"}')).toBe(false)
  })

  it('web og opgave kraever deres form', () => {
    expect(kanTegneKrop('web', '{"results":[{"url":"u","title":"t"}]}')).toBe(true)
    expect(kanTegneKrop('web', '{"results":[{"text":"x"}]}')).toBe(false)
    expect(kanTegneKrop('opgave', '{"todos":[{"content":"a"}]}')).toBe(true)
  })

  it('skriv, fejl og underagent tegner altid naar der er et resultat', () => {
    expect(kanTegneKrop('skriv', '{"status":"ok"}')).toBe(true)
    expect(kanTegneKrop('fejl', '{"status":"error"}')).toBe(true)
    expect(kanTegneKrop('underagent', '{"agent_id":"a"}')).toBe(true)
    expect(kanTegneKrop('skriv', '')).toBe(false)
  })
})
