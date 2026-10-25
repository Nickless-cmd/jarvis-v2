import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bell, RefreshCw, Search } from 'lucide-react'
import {
  afgoerNotifikation, hentNotifikationer, hentTidligere, setNotifikation,
  type Notifikation, type TidligereNotifikation,
} from '../../lib/notifikationerApi'
import { formatRelativeTime } from '../../lib/formatTime'
import { SettingsActionError, SettingsState } from '../settings/SettingsState'
import type { ApiConfig } from '../../lib/api'
import '../../styles/notifikationer-side.css'

/**
 * Alle notifikationer — historikken som sin egen flade i Arbejde.
 *
 * Bjørn 25/10-2026: «det er et notification feed, ikk en lokal historie bog..
 * så skal vi lave en side i arbejds mode hvor man kan hente og se alle
 * tidligere notifikationer».
 *
 * ## Hvorfor den er her og ikke i popoveren
 * Popoveren ved klokken er et FEED: de nyeste, kort, uden faner. Historikken
 * var før en fane i samme rude, hvilket betød at feedet bar en tabel over
 * tusindvis af afgjorte rækker ind i et panel der er 380 px bredt. Det er to
 * forskellige læseopgaver — «hvad skal jeg svare på nu» og «hvad skete der» —
 * og de skulle ikke dele plads.
 *
 * ## Nyeste øverst, altid
 * Åbne OG afgjorte i ÉN liste sorteret på `oprettet` synkende. En åben post
 * fra i går hører under en afgjort fra i dag, for tiden er den eneste akse
 * der gælder når man leder efter «hvad skete der omkring klokken 14».
 * Handlingsknapperne følger posten, ikke dens placering.
 *
 * ## Paginering, ikke et loft
 * Historikken er målt til flere tusinde rækker. Vi viser 60 og lægger 60 til
 * ad gangen — et hårdt loft ville gøre de ældste poster usynlige uden at
 * sige det, og det er præcis den slags tavse grænse fladen findes for at
 * undgå.
 */

const SIDE = 60

/** Én post fra enten den åbne liste eller historikken. `aaben` styrer hvad
 *  der kan trykkes på — ikke hvordan rækken ser ud. */
interface Raekke {
  post: Notifikation | TidligereNotifikation
  aaben: boolean
}

function erTidligere(p: Notifikation | TidligereNotifikation): p is TidligereNotifikation {
  return 'udfald_tekst' in p
}

export function NotifikationerPanel({ config, onAabnSession }: {
  config: ApiConfig
  onAabnSession?: (sessionId: string) => void
}) {
  const [aabne, setAabne] = useState<Notifikation[] | null>(null)
  const [historik, setHistorik] = useState<TidligereNotifikation[] | null>(null)
  const [fejl, setFejl] = useState(false)
  const [handlingFejl, setHandlingFejl] = useState('')
  const [travl, setTravl] = useState('')
  const [soegning, setSoegning] = useState('')
  const [slagsFilter, setSlagsFilter] = useState('')
  const [visAntal, setVisAntal] = useState(SIDE)

  const hent = useCallback(() => {
    setFejl(false)
    // To ruter, to levetider: de åbne hydreres og kan forsvinde midt i en
    // læsning, historikken er frossen. Fejler kun den ene, skal den anden
    // stadig vises — derfor allSettled og ikke Promise.all.
    void Promise.allSettled([
      hentNotifikationer(config).then((f) => setAabne(f.poster)),
      hentTidligere(config).then((f) => setHistorik(f.poster)),
    ]).then((resultater) => {
      if (resultater.every((r) => r.status === 'rejected')) setFejl(true)
    })
  }, [config])

  useEffect(() => { hent() }, [hent])

  const raekker: Raekke[] = useMemo(() => {
    const alle: Raekke[] = [
      ...(aabne ?? []).map((post) => ({ post, aaben: true })),
      ...(historik ?? []).map((post) => ({ post, aaben: false })),
    ]
    alle.sort((a, b) => {
      const ta = new Date(a.post.oprettet).getTime() || 0
      const tb = new Date(b.post.oprettet).getTime() || 0
      return tb - ta
    })
    return alle
  }, [aabne, historik])

  const slagsValg = useMemo(() => {
    const saet = new Set<string>()
    for (const r of raekker) if (r.post.slags) saet.add(r.post.slags)
    return [...saet].sort()
  }, [raekker])

  const filtreret = useMemo(() => {
    const q = soegning.trim().toLowerCase()
    return raekker.filter((r) => {
      if (slagsFilter && r.post.slags !== slagsFilter) return false
      if (!q) return true
      return `${r.post.titel} ${r.post.tekst}`.toLowerCase().includes(q)
    })
  }, [raekker, soegning, slagsFilter])

  // Et nyt søgeord må ikke efterlade brugeren på side 7 af et kortere resultat.
  useEffect(() => { setVisAntal(SIDE) }, [soegning, slagsFilter])

  const synlige = filtreret.slice(0, visAntal)

  const afgoer = async (id: string, godkendt: boolean) => {
    setTravl(id); setHandlingFejl('')
    try {
      const svar = await afgoerNotifikation(config, id, godkendt)
      if (!svar.ok) { setHandlingFejl(svar.fejl || 'Svaret kunne ikke sendes.'); return }
      hent()
    } catch {
      setHandlingFejl('Svaret kunne ikke sendes. Prøv igen.')
    } finally { setTravl('') }
  }

  const klaret = async (id: string) => {
    setTravl(id); setHandlingFejl('')
    try {
      await setNotifikation(config, id)
      hent()
    } catch {
      setHandlingFejl('Notifikationen kunne ikke afsluttes. Prøv igen.')
    } finally { setTravl('') }
  }

  const indlaeser = aabne === null && historik === null

  return (
    <div className="notifside">
      <div className="notifside-vaerktoej">
        <label className="notifside-soeg">
          <Search size={14} aria-hidden="true" />
          <input
            type="search"
            value={soegning}
            onChange={(e) => setSoegning(e.target.value)}
            placeholder="Søg i titel og tekst"
            aria-label="Søg i notifikationer"
          />
        </label>
        <select
          className="notifside-filter"
          value={slagsFilter}
          onChange={(e) => setSlagsFilter(e.target.value)}
          aria-label="Filtrér på slags"
        >
          <option value="">Alle slags</option>
          {slagsValg.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <span className="notifside-tal">
          {filtreret.length} af {raekker.length}
        </span>
        <button type="button" className="notifside-opdater" onClick={hent} aria-label="Opdater">
          <RefreshCw size={14} />
        </button>
      </div>

      <SettingsActionError message={handlingFejl} />

      {fejl ? (
        <div className="settings-feedback error" role="alert">
          <p>Notifikationerne kunne ikke hentes.</p>
          <button type="button" onClick={hent}>Prøv igen</button>
        </div>
      ) : indlaeser ? (
        <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
      ) : filtreret.length === 0 ? (
        <p className="settings-hint">
          {raekker.length === 0
            ? 'Ingen notifikationer endnu.'
            : 'Ingen notifikationer matcher søgningen.'}
        </p>
      ) : (
        <>
          <ul className="notifside-liste">
            {synlige.map(({ post, aaben }) => (
              <li key={post.id} className={`notifside-post${aaben ? ' er-aaben' : ''}`}>
                <div
                  className="notifside-hoved"
                  role={onAabnSession && post.session_id ? 'button' : undefined}
                  tabIndex={onAabnSession && post.session_id ? 0 : undefined}
                  title={post.tekst || post.titel}
                  onClick={() => { if (onAabnSession && post.session_id) onAabnSession(post.session_id) }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && onAabnSession && post.session_id) onAabnSession(post.session_id)
                  }}
                >
                  <span className="notifside-ikon"><Bell size={14} aria-hidden="true" /></span>
                  <span className="notifside-titel">{post.titel}</span>
                  <span className="notifside-tid">{formatRelativeTime(post.oprettet)}</span>
                </div>
                {post.tekst && post.tekst !== post.titel && (
                  <p className="notifside-tekst">{post.tekst}</p>
                )}
                {erTidligere(post) && post.udfald_tekst && (
                  <p className="notifside-udfald">{post.udfald_tekst}</p>
                )}
                <div className="notifside-meta">
                  <span className="notifside-slags">{post.slags}</span>
                  {aaben && post.kan_afgoere && (
                    <span className="notifside-handlinger">
                      <button type="button" disabled={travl === post.id}
                              onClick={() => void afgoer(post.id, true)}>Godkend</button>
                      <button type="button" disabled={travl === post.id}
                              onClick={() => void afgoer(post.id, false)}>Afvis</button>
                    </span>
                  )}
                  {aaben && !post.kan_afgoere && (
                    <button type="button" className="notifside-klar" disabled={travl === post.id}
                            onClick={() => void klaret(post.id)}>Marker klaret</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
          {filtreret.length > synlige.length && (
            <button type="button" className="notifside-mere"
                    onClick={() => setVisAntal((n) => n + SIDE)}>
              Vis flere ({filtreret.length - synlige.length} tilbage)
            </button>
          )}
        </>
      )}
    </div>
  )
}
