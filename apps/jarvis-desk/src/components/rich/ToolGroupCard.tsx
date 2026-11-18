import { memo, useMemo, useState } from 'react'
import { ChevronDown, Code2 } from 'lucide-react'
import type { ToolGroupBlock } from '../../lib/toolRounds'
import { summarizeRound, summerDiff } from '../../lib/toolRound'
import { KLOKKE_EFTER_S, useLoebendeTid } from '../../lib/useLoebendeTid'
import { Prikker, udenEllipse } from './Prikker'
import { Fold } from './Fold'
import { LabelSkift, formatTid } from './LabelSkift'
import { ToolCard } from './ToolCard'
import { MarkdownRenderer } from './MarkdownRenderer'

/**
 * Én sammenfoldet linje for en HEL runde værktøjsarbejde — 1:1 med mobilens
 * `InlineToolGroup` (Bjørn 8/9-2026: «det skal lige 1:1»).
 *
 *     fortælling
 *     </> Kørte agent.ts
 *     fortælling
 *     </> Kørte 2 ting  ›
 *
 * Linjen ændrer sig mens runden kører («Læser 3 filer») og lander på sin datid
 * når den er færdig. Trykker man, folder den ud.
 *
 * Én forskel fra mobilen, og den er bevidst: mobilen skjuler chevronen ved ét
 * kald, fordi den intet har at folde ud. Desk HAR noget — diff, output,
 * argumenter — så chevronen står der. Reglen er den samme (chevron hvis der er
 * noget bag den); det er kun svaret der er forskelligt, fordi funktionen er.
 */
function ToolGroupCardImpl({
  block,
  density,
  etiket,
}: {
  block: ToolGroupBlock
  density: 'compact' | 'full'
  /**
   * Rundens sætning — «Rettede fejl i login».
   *
   * Skrevet af en lille lokal model på serveren og slået op på kaldets id.
   * Den ERSTATTER den mekaniske tekst (Claude Desktop 1:1, 19/9-2026); før
   * stod den som overskrift over linjen. Udeladt = den mekaniske tekst.
   * Kommer live fra streamen og gemt fra beskedens tool_use_summary-blokke.
   */
  etiket?: string
}) {
  // En samlet tanke ER forløbet — den skal ikke gemmes bag endnu en fold, når
  // man netop har åbnet arbejdsvisningen for at se hvad der skete. En almindelig
  // runde starter lukket, som før; tanken starter åben og kan lukkes manuelt.
  //
  // Målt 18/11-2026: uden denne gren lå mellemteksten to klik væk (turhoved →
  // række), og to eksisterende tests fangede det med det samme. Det er den
  // rigtige slags fejl — kontrakten «syntesen skal kunne læses i folden» er
  // ældre end sammenlægningen og gælder stadig.
  const [aabenManuelt, setAabenManuelt] = useState<boolean | null>(null)
  const open = aabenManuelt ?? !!block.dele
  // Beregnes kun når rundens værktøjer faktisk ændrer sig (se memo nederst).
  const resume = useMemo(() => summarizeRound(block.tools), [block.tools])
  const sum = useMemo(() => summerDiff(block.tools), [block.tools])
  const koerer = block.tools.some((t) => (t.status ?? 'running') === 'running')
  // Live tid for runden, fra det første kald der stadig kører (Bjørn 17/9-2026:
  // live metadata i stedet for en linje der står stille til kaldet er færdigt).
  const startet = block.tools
    .filter((t) => (t.status ?? 'running') === 'running' && t.startet != null)
    .reduce<number | undefined>((min, t) => (min == null || t.startet! < min ? t.startet : min), undefined)
  const sek = useLoebendeTid(koerer && startet != null, startet)
  // Klokken venter mens linjen KØRER (se KLOKKE_EFTER_S): et kald på to
  // sekunder skal ikke nå at vise «0 s» og skifte. Er runden færdig, vises det
  // målte tal med det samme — der er ingen flimren at undgå, og tallet er
  // information man vil have.
  const visSek = sek == null || (koerer && sek < KLOKKE_EFTER_S) ? null : Math.floor(sek)
  if (!resume) return null
  // Claude Desktop 1:1 (19/9-2026, læst i `Tf`: `summary || … || mekanisk`):
  // modellens sætning ERSTATTER den mekaniske tekst, når den findes. Før stod
  // den som overskrift OVER linjen.
  // Hukommelsesskrivning skal følge det faktiske resultat. En genereret
  // rundetekst kan stadig sige "Huskede remember_this" eller påstå succes ved fejl.
  const erMinde = block.tools.length === 1 && block.tools[0]?.name.replace(/^operator_/, '') === 'remember_this'
  const tekniskEtiket = block.tools.some((tool) => {
    const escaped = tool.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    return etiket && new RegExp(`(^|\\W)${escaped}(?=\\W|$)`).test(etiket)
  })
  // To linjer, to tider (Bjørn 18/11-2026): «det aktive runde linje skal være
  // nutid og den færdige runde linjes samlet forløb datid».
  //
  // `summarizeRound` skifter selv til datid når intet kører («Læser 3 filer»
  // → «Læste 3 filer»), så skiftet er netop `koerer` — der skal ingen
  // datids-tabel ved siden af. Men `etiket` beskriver et AFLUTTET forløb, og
  // før vandt den ubetinget: så stod den kørende runde i datid om noget der
  // ikke var sket endnu. Kommentaren her antog at etiketten «først kommer når
  // runden er talt op» — den antagelse holdt ikke, så nu håndhæves den.
  const tekst = koerer
    ? udenEllipse(resume)
    : (!erMinde && etiket && !tekniskEtiket ? etiket : resume)

  return (
    <div className={`toolgroup${koerer ? ' er-koerende' : ''}${open ? ' er-aaben' : ''}${block.dele ? ' er-tanke' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={open}
        aria-label={tekst}
        onClick={() => setAabenManuelt((o) => !(o ?? !!block.dele))}
      >
        {/* `</>` står fast foran linjen — også når runden er færdig (Bjørn
            19/9-2026: «må gerne komme tilbage»). Claude Desktop viser kun
            glyfen mens der arbejdes; her er det et bevidst valg. */}
        <span className="toolgroup-spark" aria-hidden="true">
          <Code2 size={15} className="toolgroup-icon" strokeWidth={1.8} />
        </span>
        <span className="toolgroup-label">
          <LabelSkift
            tekst={tekst}
            arbejder={koerer}
            className={koerer ? 'shimmer' : ''}
            fastIkon
          />
        </span>
        {/* Klokken i kildens format («12s», «1m 5s») og med dens 65 % —
            tallet må ikke konkurrere med labelen. */}
        {visSek != null
          ? <span className="linje-tid" data-testid="runde-tid">{formatTid(visSek)}</span>
          : null}
        {/* Summen i selve linjen, 1:1 med mobilen: foldet som standard ville
            tallene ellers kun ses af den der folder ud. Et nul vises ikke. */}
        {sum ? (
          <span className="toolgroup-diffstat" data-testid="toolgroup-diffstat">
            {sum.add ? <span className="git-add">+{sum.add}</span> : null}
            {sum.add && sum.del ? ' ' : null}
            {sum.del ? <span className="git-del">−{sum.del}</span> : null}
          </span>
        ) : null}
        {/* Prikker og caret i SAMME celle. Mens runden kører står prikkerne
            fremme; ved hover eller tastaturfokus krydsfader de til careten
            (200 ms). Careten er én glyf der drejes -90° når runden er foldet,
            så åbn/luk er en drejning og ikke et ikon-bytte. */}
        <span className="toolgroup-celle" data-testid="tool-status-caret">
          <Prikker live={koerer} />
          <ChevronDown size={15} className="toolgroup-chevron" strokeWidth={1.8} />
        </span>
      </button>
      <Fold aaben={open}>
        <div className="toolgroup-body">
          {/* `dele` er hele tanken i rækkefølge (kald og mellemtekst blandet);
              uden den er rækken én runde, som før. Mellemteksten er ikke en
              arbejdsdetalje der skal skjules — den er det der binder kaldene
              sammen til et forløb, så den står på sin egen plads mellem dem. */}
          {block.dele
            ? block.dele.map((del, i) => (
                del.slags === 'kald'
                  ? <ToolCard key={del.kald.id} block={del.kald} density={density} />
                  : (
                    <div className="toolgroup-mellemtekst" key={`tekst-${i}`}>
                      <MarkdownRenderer text={del.tekst} streaming={false} />
                    </div>
                  )
              ))
            : block.tools.map((t) => (
                <ToolCard key={t.id} block={t} density={density} />
              ))}
        </div>
      </Fold>
    </div>
  )
}

/**
 * Memoiseret på værktøjernes IDENTITET (profileret 19/9-2026): under streaming
 * bygger groupToolRounds nye rund-objekter ved hver delta, men selve
 * tool_use-blokkene er de samme — reduceren udskifter kun den blok der
 * ændrer sig. Uden memo genberegnede HVER runde i svaret sin opsummering og
 * diff-sum (summarizeRound/summerDiff) ved hver delta: 4,5 % af en streaming
 * i profilen, og en del af de 34 ms-renders der tabte frames.
 */
export const ToolGroupCard = memo(ToolGroupCardImpl, (a, b) => {
  if (a.density !== b.density || a.etiket !== b.etiket) return false
  if (a.block.tools.length !== b.block.tools.length) return false
  if (!a.block.tools.every((t, i) => t === b.block.tools[i])) return false
  // `dele` kan ændre sig mens kaldene er de samme — en mellemtekst der vokser
  // under streamen. Uden denne sammenligning ville rækken stå frosset med den
  // tekst der stod da den blev memoiseret.
  const da = a.block.dele
  const db = b.block.dele
  if ((da?.length ?? -1) !== (db?.length ?? -1)) return false
  if (!da) return true
  return da.every((del, i) => {
    const anden = db![i]
    if (!anden || anden.slags !== del.slags) return false
    return del.slags === 'kald'
      ? del.kald === (anden as { kald: unknown }).kald
      : del.tekst === (anden as { tekst: string }).tekst
  })
})
