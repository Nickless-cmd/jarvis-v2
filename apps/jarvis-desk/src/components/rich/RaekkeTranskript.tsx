/**
 * Rækkevisningen: transskriptet som en flad hændelsesrække.
 *
 * ## Hvad den er
 *
 * Et alternativ til bobblevisningen, bag en knap. Hver hændelse — tanke,
 * værktøjskald, kontekstindsprøjtning — er ÉN række af samme form og samme
 * højde. Arbejdet folder sig sammen bag én linje når turen er slut; kun
 * svaret bliver stående.
 *
 * ## Hvorfor den føles glat
 *
 * Det er ikke animation. Det er at intet skifter højde mens svaret streamer:
 * rækken er 24px før, under og efter, og teksten klippes i stedet for at
 * ombryde. `contain: size layout` sidder ÉT sted — på den sammenfoldede
 * tænke-række — præcis som i forlægget.
 *
 * ## Hvad den IKKE rører
 *
 * Composer, liveness-indikator og save-rail (Bjørn 22/9-2026: «vores composer
 * og liveness indikator og savedrail osv. Skal blive»). Kun transskriptet.
 * Prosaen går stadig gennem `BlocksRenderer`, så markdown, kodeblokke og
 * billeder er nøjagtig som i bobblevisningen.
 */
import { memo, useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import type { ApiConfig } from '../../lib/api'
import { opdel, turHoved, type ArbejdsElement } from '../../lib/raekkeModel'
import { lookupTool } from '../../lib/toolRegistry'
import { subjectFromInput } from '../../lib/toolRound'
import { postFor, kropFor } from './raekkeKroppe'
import { BlocksRenderer } from './BlocksRenderer'

/** Første linje af en tanke — resten ligger i kroppen. */
function foersteLinje(s: string): string {
  const t = s.trim().split('\n').find((l) => l.trim()) ?? ''
  return t.trim()
}

function Raekke({
  glyf, slags, sum, krop, koerer, fejl, tanke,
}: {
  glyf: string
  slags: string
  sum: string
  krop?: React.ReactNode
  koerer?: boolean
  fejl?: boolean
  tanke?: boolean
}) {
  const [aaben, setAaben] = useState(false)
  const foldbar = krop != null
  return (
    <div
      className="rv-r"
      {...(foldbar ? { 'data-foldbar': '' } : {})}
      {...(aaben ? { 'data-aaben': '' } : {})}
      {...(koerer ? { 'data-koerer': '' } : {})}
      {...(fejl ? { 'data-fejl': '' } : {})}
      {...(tanke ? { 'data-tanke': '' } : {})}
      {...(foldbar
        ? { role: 'button', tabIndex: 0, 'aria-expanded': aaben, onClick: () => setAaben((v) => !v),
            onKeyDown: (e: React.KeyboardEvent) => {
              if (e.key !== 'Enter' && e.key !== ' ') return
              e.preventDefault(); setAaben((v) => !v)
            } }
        : {})}
    >
      <div className="rv-hoved">
        <span className="rv-ikon" aria-hidden="true">{glyf}</span>
        <span className="rv-slags">{slags}</span>
        {sum ? (
          <>
            <span className="rv-sep" aria-hidden="true" />
            {/* Mens raekken koerer foelger teksten ENDEN — ellers ser man kun
                begyndelsen af en lang tanke, og raekken virker doed. */}
            <span className="rv-sum" {...(koerer ? { 'data-foelg-ende': '' } : {})}>
              <span className="rv-sumT">{sum}</span>
            </span>
          </>
        ) : <span className="rv-sum" />}
        {foldbar && <span className="rv-chev" aria-hidden="true">{aaben ? '▾' : '▸'}</span>}
      </div>
      {foldbar && aaben && <div className="rv-krop">{krop}</div>}
    </div>
  )
}

function Element({ e, streaming }: { e: ArbejdsElement; streaming: boolean }) {
  if (e.slags === 'mellemsvar') {
    // Jarvis' korte narration MELLEM kaldene. Den bor i gruppen og folder sig
    // sammen med arbejdet — den er ikke en besked (Bjoern 22/9-2026).
    return <div className="rv-mellem">{e.tekst}</div>
  }
  const b = e.blok
  if (b.type === 'thinking') {
    return (
      <Raekke
        tanke glyf="✳" slags="Think"
        sum={foersteLinje(b.thinking)}
        koerer={streaming && !b.seconds}
        krop={<div className="rv-kort"><pre>{b.thinking}</pre></div>}
      />
    )
  }
  if (b.type === 'skill_surface') {
    return <Raekke glyf="◈" slags="Skill" sum={b.matches.map((m) => m.name).join(' · ')} />
  }
  if (b.type === 'tool_use') {
    const { etiket } = postFor(b.name)
    const meta = lookupTool(b.name)
    const fejl = b.status === 'error'
    // `input` er TOMT mens argumenterne stroemmer ind — de ligger i
    // `partialJson` imens (toolRound.ts:142). Bruger man kun registrets
    // `summarize`, staar raekken tom netop mens den er mest interessant, og
    // fyldes foerst naar hele svaret er faerdigt (Bjoern 23/9-2026).
    // `subjectFromInput` er bobblevisningens egen loesning paa praecis det.
    const emne = subjectFromInput(b.input, b.partialJson) || meta.summarize(b.input, b.result)
    return (
      <Raekke
        glyf="▸" slags={etiket}
        sum={emne}
        koerer={b.status === 'running'}
        fejl={fejl}
        krop={kropFor(b.name, b.input, b.result, fejl)}
      />
    )
  }
  return null
}

function RaekkeTranskriptImpl({
  blocks, streaming, beskedId, config,
}: {
  blocks: ContentBlock[]
  streaming: boolean
  beskedId?: string
  config?: ApiConfig
}) {
  const { arbejde, svar, kald, sekunder } = opdel(blocks)
  // Aaben mens der arbejdes, lukket naar turen er slut — man skal kunne
  // FOELGE MED, og bagefter skal rodet vaek (Bjoern 22/9-2026).
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  const aaben = aabenManuelt ?? streaming

  return (
    <div className="raekkevisning">
      {arbejde.length > 0 && (
        <>
          <button
            type="button" className="rv-tur" aria-expanded={aaben}
            onClick={() => setAabenManuelt(!aaben)}
          >
            <span className="rv-turC" aria-hidden="true">{aaben ? '▾' : '▸'}</span>
            {/* `shimmer` er desks egen regel (app.css) — 2.25s, pinned 1:1 mod
                Claude Desktop af tokens.test.ts. Vi laaner den, vi laver ikke
                en ny. Kun mens der faktisk arbejdes. */}
            {streaming && aabenManuelt === null
              ? <span className="shimmer">Working…</span>
              : <span>{turHoved(kald, sekunder)}</span>}
          </button>
          <div className="rv-gruppe" hidden={!aaben}>
            {arbejde.map((e, i) => <Element key={i} e={e} streaming={streaming} />)}
          </div>
        </>
      )}
      {svar.length > 0 && (
        <div className="rv-svar">
          <BlocksRenderer
            blocks={svar} density="compact" streaming={streaming}
            beskedId={beskedId} config={config}
          />
        </div>
      )}
    </div>
  )
}

export const RaekkeTranskript = memo(RaekkeTranskriptImpl)
