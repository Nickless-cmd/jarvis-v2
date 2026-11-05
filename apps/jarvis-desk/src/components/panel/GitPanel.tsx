import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowUp, GitBranch, Loader2, Minus, Plus, RefreshCw } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { opretWorktree } from '../../lib/gitWorkspace'
import {
  commitKlar, commitStaged, diffModeForSektion, filNavn, grupperFiler, hentGitDiff, hentGitLog,
  hentGitStatus, hentGitWorktrees, kanPushe, parseDiff, pushBranch, stageFiler, statusEtiket,
  trackingTekst, unstageFiler,
  type GitCommitPost, type GitFil, type GitStatusPanel, type GitWorktree, type Maal,
} from '../../lib/gitPanel'
import { BranchVaelger } from '../code/BranchVaelger'

type Sektion = 'staged' | 'aendret' | 'nye' | 'konflikt'
const SEKTION_TITEL: Record<Sektion, string> = {
  konflikt: 'Konflikter', staged: 'Staged', aendret: 'Ændringer', nye: 'Nye filer',
}

const fejlTekst = (e: unknown, standard: string) =>
  e instanceof Error && e.message ? e.message : standard

/** Git-panel i code-fladen: branch + status, ændrede filer, diff, stage/unstage,
 *  commit (serveren sætter attribution-traileren), push, branch-skift og worktrees.
 *
 *  Panelet har ingen egen git-logik: alt går gennem `/chat/git-panel/*` og de
 *  eksisterende `/chat/git/checkout|worktree`-ruter. */
export function GitPanel({
  config, kind, root,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
}) {
  const maal: Maal = useMemo(() => ({ kind, root }), [kind, root])
  const [status, setStatus] = useState<GitStatusPanel | null>(null)
  const [fejl, setFejl] = useState('')
  const [besked, setBesked] = useState('')
  const [arbejder, setArbejder] = useState('')
  const [info, setInfo] = useState('')
  const [valgt, setValgt] = useState<{ path: string; sektion: Sektion } | null>(null)
  const [diff, setDiff] = useState<{ tekst: string; afkortet: boolean; binaer: boolean; fejl: string } | null>(null)
  const [bekraeftPush, setBekraeftPush] = useState(false)
  const [log, setLog] = useState<GitCommitPost[]>([])
  const [trær, setTrær] = useState<GitWorktree[]>([])
  const [nytTrae, setNytTrae] = useState('')

  const opdater = useCallback(async () => {
    try {
      const s = await hentGitStatus(config, maal)
      setStatus(s)
      setFejl(s.ok ? '' : (s.error || 'Kunne ikke læse git-status'))
      if (!s.ok) return
      const [l, w] = await Promise.all([
        hentGitLog(config, maal, 15).catch(() => null),
        hentGitWorktrees(config, maal).catch(() => null),
      ])
      if (l?.ok) setLog(l.commits)
      if (w?.ok) setTrær(w.worktrees)
    } catch (e) {
      setFejl(fejlTekst(e, 'Kunne ikke læse git-status'))
    }
  }, [config, maal])

  useEffect(() => { void opdater() }, [opdater])

  // Diff for den valgte fil. Forsvinder filen fra listen (fx efter commit),
  // nulstilles valget i stedet for at vise en diff der ikke længere findes.
  useEffect(() => {
    if (!valgt) { setDiff(null); return }
    let annulleret = false
    hentGitDiff(config, maal, valgt.path, diffModeForSektion(valgt.sektion))
      .then((r) => {
        if (annulleret) return
        setDiff({ tekst: r.diff, afkortet: r.truncated, binaer: r.binary, fejl: r.ok ? '' : (r.error || 'Kunne ikke hente diff') })
      })
      .catch((e) => { if (!annulleret) setDiff({ tekst: '', afkortet: false, binaer: false, fejl: fejlTekst(e, 'Kunne ikke hente diff') }) })
    return () => { annulleret = true }
  }, [config, maal, valgt, status])

  useEffect(() => {
    if (!valgt || !status) return
    const findes = status.files.some((f) => f.path === valgt.path)
    if (!findes) setValgt(null)
  }, [status, valgt])

  const kør = async (
    navn: string,
    fn: () => Promise<{ ok: boolean; error?: string }>,
    ok = '',
  ): Promise<{ ok: boolean; error?: string } | undefined> => {
    if (arbejder) return undefined
    setArbejder(navn); setFejl(''); setInfo('')
    try {
      const r = await fn()
      if (!r.ok) setFejl(r.error || 'Handlingen lykkedes ikke')
      else if (ok) setInfo(ok)
      return r
    } catch (e) {
      setFejl(fejlTekst(e, 'Handlingen lykkedes ikke'))
      return undefined
    } finally {
      setArbejder('')
      await opdater()
    }
  }

  const grupper = useMemo(() => grupperFiler(status?.files ?? []), [status])
  const klar = commitKlar(status, besked)

  const commit = async () => {
    if (!klar.klar) return
    const r = await kør('commit', () => commitStaged(config, maal, besked.trim()))
    if (r?.ok) { setBesked(''); setInfo(`Committed ${(r as { sha?: string }).sha ?? ''}`.trim()) }
  }

  const push = async () => {
    setBekraeftPush(false)
    const r = await kør('push', () => pushBranch(config, maal))
    if (r?.ok) setInfo('Pushet ✓')
  }

  const opret = async () => {
    const navn = nytTrae.trim()
    if (!navn) return
    const r = await kør('worktree', () => opretWorktree(config, { kind, root, name: navn }), 'Worktree oprettet')
    if (r?.ok) setNytTrae('')
  }

  const række = (f: GitFil, sektion: Sektion) => {
    const { navn, mappe } = filNavn(f.path)
    const aktiv = valgt?.path === f.path && valgt.sektion === sektion
    return (
      <li key={`${sektion}:${f.path}`} className={`gitpanel-fil ${aktiv ? 'active' : ''}`}>
        <button type="button" className="gitpanel-fil-navn" title={f.path}
          onClick={() => setValgt({ path: f.path, sektion })}>
          <span className={`gitpanel-kode kode-${sektion}`}>{statusEtiket(f, sektion)}</span>
          <span className="gitpanel-sti">{navn}</span>
          {mappe && <span className="gitpanel-mappe">{mappe}</span>}
        </button>
        {sektion === 'staged' ? (
          <button type="button" className="gitpanel-ikon" disabled={!!arbejder}
            title="Fjern fra staged" aria-label={`Unstage ${f.path}`}
            onClick={() => void kør('unstage', () => unstageFiler(config, maal, [f.path]))}>
            <Minus size={12} />
          </button>
        ) : sektion !== 'konflikt' && (
          <button type="button" className="gitpanel-ikon" disabled={!!arbejder}
            title="Stage" aria-label={`Stage ${f.path}`}
            onClick={() => void kør('stage', () => stageFiler(config, maal, [f.path]))}>
            <Plus size={12} />
          </button>
        )}
      </li>
    )
  }

  const sektion = (s: Sektion) => {
    const liste = grupper[s]
    if (liste.length === 0) return null
    return (
      <section className="gitpanel-sektion" key={s}>
        <h4>
          {SEKTION_TITEL[s]} <span className="gitpanel-antal">{liste.length}</span>
          {s === 'staged' && (
            <button type="button" className="gitpanel-lille" disabled={!!arbejder}
              onClick={() => void kør('unstage', () => unstageFiler(config, maal, [], true))}>
              Unstage alle
            </button>
          )}
          {(s === 'aendret' || s === 'nye') && (
            <button type="button" className="gitpanel-lille" disabled={!!arbejder}
              onClick={() => void kør('stage', () => stageFiler(config, maal, liste.map((f) => f.path)))}>
              Stage alle
            </button>
          )}
        </h4>
        <ul>{liste.map((f) => række(f, s))}</ul>
      </section>
    )
  }

  const parsed = diff ? parseDiff(diff.tekst) : null

  if (!status) {
    return <div className="gitpanel"><div className="gitpanel-tom">
      {fejl || <><Loader2 size={13} className="spin" /> Henter git-status…</>}
    </div></div>
  }

  return (
    <div className="gitpanel">
      <div className="gitpanel-top">
        {status.ok ? (
          <BranchVaelger config={config} kind={kind} root={root} aktuel={status.branch}
            onSkiftet={() => { setValgt(null); void opdater() }} />
        ) : (
          <span className="gitpanel-branch"><GitBranch size={13} /> —</span>
        )}
        <span className={`gitpanel-dirty ${status.dirty ? 'dirty' : 'clean'}`}>
          {status.dirty ? `${status.dirty} ændrede filer` : 'Rent træ'}
        </span>
        <span className="gitpanel-tracking">{status.ok ? trackingTekst(status) : ''}</span>
        <span className="gitpanel-fyld" />
        {bekraeftPush ? (
          <span className="gitpanel-bekraeft">
            Push {status.branch}?
            <button type="button" className="gitpanel-lille" onClick={() => void push()}>Ja, push</button>
            <button type="button" className="gitpanel-lille" onClick={() => setBekraeftPush(false)}>Annullér</button>
          </span>
        ) : (
          <button type="button" className="gitpanel-knap" disabled={!!arbejder || !kanPushe(status)}
            title={kanPushe(status) ? 'Push til remote' : 'Intet at pushe'}
            onClick={() => setBekraeftPush(true)}>
            {arbejder === 'push' ? <Loader2 size={12} className="spin" /> : <ArrowUp size={12} />} Push
          </button>
        )}
        <button type="button" className="gitpanel-ikon" title="Opdatér" aria-label="Opdatér git-status"
          disabled={!!arbejder} onClick={() => void opdater()}>
          <RefreshCw size={12} />
        </button>
      </div>

      {fejl && <div className="gitpanel-fejl" role="alert">{fejl}</div>}
      {info && !fejl && <div className="gitpanel-info" role="status">{info}</div>}

      {status.ok && (
        <div className="gitpanel-krop">
          <div className="gitpanel-venstre">
            {status.files.length === 0 && <div className="gitpanel-tom">Ingen ændringer.</div>}
            {(['konflikt', 'staged', 'aendret', 'nye'] as Sektion[]).map(sektion)}

            <div className="gitpanel-commit">
              <textarea value={besked} rows={3} placeholder="Commit-besked"
                aria-label="Commit-besked" onChange={(e) => setBesked(e.target.value)} />
              <button type="button" className="gitpanel-knap primary"
                disabled={!klar.klar || !!arbejder} title={klar.grund || 'Commit det staged'}
                onClick={() => void commit()}>
                {arbejder === 'commit' ? <Loader2 size={12} className="spin" /> : null} Commit
                {status.staged_count > 0 ? ` (${status.staged_count})` : ''}
              </button>
              {!klar.klar && besked.trim() !== '' && <span className="gitpanel-hint">{klar.grund}</span>}
              <span className="gitpanel-hint">Attribution (Actor, Run-ID m.fl.) tilføjes af serveren.</span>
            </div>

            <section className="gitpanel-sektion">
              <h4>Seneste commits</h4>
              {log.length === 0 ? <div className="gitpanel-tom">Ingen commits endnu.</div> : (
                <ul className="gitpanel-log">
                  {log.map((c) => (
                    <li key={c.sha} title={`${c.author} · ${c.date}`}>
                      <code>{c.short}</code> {c.subject}
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="gitpanel-sektion">
              <h4>Worktrees <span className="gitpanel-antal">{trær.length}</span></h4>
              <ul className="gitpanel-trae">
                {trær.map((t) => (
                  <li key={t.path} className={t.current ? 'current' : ''} title={t.path}>
                    <GitBranch size={11} /> {t.branch || (t.detached ? 'afkoblet' : '—')}
                    <span className="gitpanel-mappe">{t.path}</span>
                    {t.main && <span className="gitpanel-kode">Hoved</span>}
                    {t.locked && <span className="gitpanel-kode">Låst</span>}
                  </li>
                ))}
              </ul>
              <div className="gitpanel-nytrae">
                <input value={nytTrae} placeholder="Ny worktree (branch-navn)"
                  aria-label="Navn på ny worktree" onChange={(e) => setNytTrae(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') void opret() }} />
                <button type="button" className="gitpanel-knap" disabled={!nytTrae.trim() || !!arbejder}
                  onClick={() => void opret()}>Opret</button>
              </div>
            </section>
          </div>

          <div className="gitpanel-hoejre">
            {!valgt && <div className="gitpanel-tom">Vælg en fil for at se ændringerne.</div>}
            {valgt && (
              <>
                <div className="gitpanel-diff-hoved">
                  <span title={valgt.path}>{valgt.path}</span>
                  {parsed && (
                    <span className="gitpanel-tal">
                      <span className="git-add">+{parsed.tilfoejet}</span>{' '}
                      <span className="git-del">−{parsed.fjernet}</span>
                    </span>
                  )}
                </div>
                {!diff && <div className="gitpanel-tom"><Loader2 size={13} className="spin" /> Henter diff…</div>}
                {diff?.fejl && <div className="gitpanel-fejl">{diff.fejl}</div>}
                {diff && !diff.fejl && diff.tekst.trim() === '' && (
                  <div className="gitpanel-tom">Ingen tekstændringer at vise.</div>
                )}
                {diff?.binaer && <div className="gitpanel-hint">Binær fil — ingen linjevisning.</div>}
                {parsed && parsed.linjer.length > 0 && (
                  <pre className="gitpanel-diff">
                    {parsed.linjer.map((l, i) => (
                      <div key={i} className={`dl dl-${l.type}`}>{l.tekst || ' '}</div>
                    ))}
                  </pre>
                )}
                {diff?.afkortet && <div className="gitpanel-hint">Diffen er afkortet — den er for stor til panelet.</div>}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
