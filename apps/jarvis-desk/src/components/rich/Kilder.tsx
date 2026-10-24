import { kilderFraBlokke, kilderPrDomaene, hukommelseskilderFraBlokke } from '../../lib/kilder'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * «Kilder» under et svar — hvad svaret faktisk blev formet af.
 *
 * Desk havde ingen kilde-visning i chatten overhovedet. Den eneste fandtes i
 * kodetilstandens miljøpanel og viste et MÆRKAT («Websøgning»), ikke adresser.
 *
 * 24/10-2026: udvidet med HUKOMMELSES-kilder. Før viste rækken kun webdomæner,
 * så et svar der kom fra MEMORY.md, hjernen eller en tidligere samtale så ud
 * som om det kom ud af ingenting. `recall` har hele tiden rapporteret `source`
 * per hit — det nåede bare aldrig klienten. Nu gør det, og de to slags kilder
 * står hver for sig: en side man slog op, og en erindring man trak på.
 *
 * Tegnes kun når turen er færdig: under streaming står tool-blokkene der
 * allerede og viser det samme, og en liste der vokser mens man læser er støj.
 */
export function Kilder({ blocks }: { blocks: ContentBlock[] }) {
  const kilder = kilderPrDomaene(kilderFraBlokke(blocks))
  const hukommelse = hukommelseskilderFraBlokke(blocks)
  if (kilder.length === 0 && hukommelse.length === 0) return null
  return (
    <div className="msg-kilder" aria-label="Kilder">
      {hukommelse.length > 0 && (
        <>
          <span className="msg-kilder-head">Hukommelse</span>
          <span className="msg-kilder-liste">
            {hukommelse.map((k) => (
              <span
                key={k.kilde}
                className="msg-kilde msg-kilde-hukommelse"
                title={`${k.antal} ${k.antal === 1 ? 'hit' : 'hits'} fra ${k.kilde}`}
              >
                {k.etiket}
              </span>
            ))}
          </span>
        </>
      )}
      {kilder.length > 0 && (
        <>
          <span className="msg-kilder-head">Web</span>
          <span className="msg-kilder-liste">
            {kilder.map((k) => (
              <a
                key={k.url}
                className="msg-kilde"
                href={k.url}
                target="_blank"
                rel="noreferrer noopener"
                title={k.url}
              >
                {k.domaene}
              </a>
            ))}
          </span>
        </>
      )}
    </div>
  )
}
