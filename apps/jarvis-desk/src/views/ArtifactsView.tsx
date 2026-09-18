import { useEffect, useMemo, useState } from 'react'
import { FileCode2, Loader2, MessageSquare, Search } from 'lucide-react'
import { useSettings } from '../hooks/useSettings'
import { useSessions } from '../hooks/useSessions'
import { getFile } from '../lib/api'
import { hentArtefakter, laesKodeMappe, type Artefakt, type ArtefaktListe } from '../lib/artefakter'
import { mappeNavn } from '../lib/arbejdsmapper'
import { formatRelativeTime } from '../lib/formatTime'
import { CodeBlock } from '../components/rich/CodeBlock'
import { MarkdownRenderer } from '../components/rich/MarkdownRenderer'

/**
 * Artefakter i code mode (Bjørn 18/9-2026: «venstre panel mangler en artifakts
 * menu i code mode... det skal bygges fra bunden» — og «på tværs»).
 *
 * Én række pr. fil Jarvis har skrevet eller rettet i den valgte arbejdsmappe,
 * nyeste først, samlet på tværs af samtaler. Klik viser filen, som den står
 * NU, ved siden af listen; «samtalen» fører tilbage til dér hvor den sidst blev
 * rørt.
 *
 * Filen vises i visningen selv og ikke i inspektør-panelet. Panelet henter kun
 * fra server-roden `repo`; artefakter kan ligge i en mappe på din maskine.
 */
export function ArtifactsView({ onOpenCode }: { onOpenCode: () => void }) {
  const { settings } = useSettings()
  const { select } = useSessions()
  const base = settings?.apiBaseUrl
  const token = settings?.authToken

  const [mappe] = useState(laesKodeMappe)
  const [liste, setListe] = useState<ArtefaktListe | null>(null)
  const [fejl, setFejl] = useState('')
  const [søg, setSøg] = useState('')
  const [valgt, setValgt] = useState<Artefakt | null>(null)
  const [fil, setFil] = useState<{ content: string; language: string } | null>(null)
  const [filFejl, setFilFejl] = useState('')

  useEffect(() => {
    if (!base) return
    let levende = true
    setFejl('')
    hentArtefakter({ apiBaseUrl: base, authToken: token ?? null }, mappe.root)
      .then((r) => {
        if (!levende) return
        setListe(r)
        if (!r.ok) setFejl(r.error || 'Kunne ikke hente artefakter')
      })
      .catch((e) => { if (levende) setFejl(e instanceof Error && e.message ? e.message : 'Kunne ikke hente artefakter') })
    return () => { levende = false }
  }, [base, token, mappe.root])

  // Filen hentes som den står NU — ikke som Jarvis efterlod den. Står der
  // noget andet end hans sidste ændring, er det den sandhed man skal se.
  useEffect(() => {
    setFil(null); setFilFejl('')
    if (!valgt || !base) return
    let levende = true
    getFile({ apiBaseUrl: base, authToken: token ?? null }, mappe.root, valgt.rel, mappe.kind)
      .then((d) => { if (levende) setFil({ content: d.content, language: d.language }) })
      .catch(() => { if (levende) setFilFejl('Filen kunne ikke hentes — den kan være flyttet eller slettet siden') })
    return () => { levende = false }
  }, [valgt, base, token, mappe.root, mappe.kind])

  const synlige = useMemo(() => {
    const q = søg.trim().toLowerCase()
    const alle = liste?.artifacts ?? []
    return q ? alle.filter((a) => a.rel.toLowerCase().includes(q)) : alle
  }, [liste, søg])

  const åbnSamtale = (sid: string) => { if (sid) { select(sid); onOpenCode() } }

  return (
    <div className="artefakter">
      <div className="artefakter-liste">
        <div className="artefakter-hoved">
          <div className="artefakter-titel">Artefakter</div>
          <div className="artefakter-mappe" title={liste?.root || mappe.root}>
            {mappeNavn(liste?.root || mappe.root)}
            {liste?.ok && <span className="artefakter-antal"> · {liste.total} filer</span>}
          </div>
        </div>
        <div className="artefakter-soeg">
          <Search size={13} />
          <input
            type="text"
            value={søg}
            placeholder="Filtrér på sti"
            aria-label="Filtrér artefakter"
            onChange={(e) => setSøg(e.target.value)}
          />
        </div>
        <div className="artefakter-raekker" role="list">
          {!liste && !fejl && <div className="artefakter-tom"><Loader2 size={13} className="spin" /> Henter…</div>}
          {fejl && <div className="artefakter-fejl">{fejl}</div>}
          {liste?.ok && synlige.length === 0 && (
            <div className="artefakter-tom">
              {søg.trim() ? 'Ingen filer matcher' : 'Jarvis har ikke skrevet eller rettet noget i denne mappe endnu'}
            </div>
          )}
          {synlige.map((a) => {
            const del = a.rel.split('/')
            const navn = del.pop() || a.rel
            const mappeDel = del.join('/')
            return (
              <button
                key={a.path}
                type="button"
                role="listitem"
                className={`artefakt-raekke${valgt?.path === a.path ? ' er-valgt' : ''}`}
                onClick={() => setValgt(a)}
                title={a.path}
              >
                <FileCode2 size={14} className="artefakt-ikon" />
                <span className="artefakt-tekst">
                  <span className="artefakt-navn">
                    {navn}
                    {(a.add > 0 || a.del > 0) && (
                      <span className="artefakt-diff">
                        {a.add > 0 && <span className="git-add">+{a.add}</span>}
                        {a.add > 0 && a.del > 0 ? ' ' : null}
                        {a.del > 0 && <span className="git-del">−{a.del}</span>}
                      </span>
                    )}
                  </span>
                  {mappeDel && <span className="artefakt-sti">{mappeDel}</span>}
                  <span className="artefakt-meta">
                    {a.last_at ? formatRelativeTime(a.last_at) : ''}
                    {a.edits > 1 ? ` · ${a.edits} ændringer` : ''}
                    {a.session_count > 1 ? ` i ${a.session_count} samtaler` : ''}
                  </span>
                </span>
              </button>
            )
          })}
        </div>
        {liste?.ok && (
          // Så et tal der ser lavt ud kan kontrolleres — ingen vindue skjuler halen.
          <div className="artefakter-fod">Læst ud af {liste.scanned} svar</div>
        )}
      </div>

      <div className="artefakter-visning">
        {!valgt && <div className="artefakter-tom">Vælg en fil for at se den, som den står nu.</div>}
        {valgt && (
          <>
            <div className="artefakt-visning-hoved">
              <span className="artefakt-visning-sti" title={valgt.path}>{valgt.rel}</span>
              {valgt.session_id && (
                <button type="button" className="artefakt-samtale" onClick={() => åbnSamtale(valgt.session_id)}
                  title="Åbn samtalen hvor filen sidst blev rørt">
                  <MessageSquare size={12} /> {valgt.session_title || 'Samtalen'}
                </button>
              )}
            </div>
            <div className="artefakt-visning-krop">
              {filFejl && <div className="artefakter-fejl">{filFejl}</div>}
              {!filFejl && !fil && <div className="artefakter-tom"><Loader2 size={13} className="spin" /> Henter…</div>}
              {fil && (/\.mdx?$/i.test(valgt.rel)
                ? <MarkdownRenderer text={fil.content} streaming={false} />
                : <CodeBlock code={fil.content} lang={fil.language || 'text'} />)}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
