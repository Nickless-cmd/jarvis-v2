import { kilderFraBlokke, kilderPrDomaene } from '../../lib/kilder'
import type { ContentBlock } from '../../lib/sseProtocol'

/**
 * «Kilder» under et svar — de sider han faktisk hentede, som klikbare links.
 *
 * Desk havde ingen kilde-visning i chatten overhovedet. Den eneste fandtes i
 * kodetilstandens miljøpanel og viste et MÆRKAT («Websøgning»), ikke adresser.
 *
 * Tegnes kun når turen er færdig: under streaming står tool-blokkene der
 * allerede og viser det samme, og en liste der vokser mens man læser er støj.
 */
export function Kilder({ blocks }: { blocks: ContentBlock[] }) {
  const kilder = kilderPrDomaene(kilderFraBlokke(blocks))
  if (kilder.length === 0) return null
  return (
    <div className="msg-kilder" aria-label="Kilder">
      <span className="msg-kilder-head">Kilder</span>
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
    </div>
  )
}
