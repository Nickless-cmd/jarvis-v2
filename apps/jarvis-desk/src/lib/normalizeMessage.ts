import type { ContentBlock } from './sseProtocol'
import { foldToolResults } from './foldToolResults'

/** Normalisér en server-besked (markdown-string) til ContentBlock[].
 *  Loadede beskeder kommer som string; streamede kommer som native blocks.
 *  Begge rendres af samme pipeline. */
export function stringToBlocks(content: string): ContentBlock[] {
  if (!content) return []
  return [{ type: 'text', text: content }]
}

/** Vælg render-blokke for en server-besked: kanonisk content_json (foldet) hvis
 *  til stede, ellers legacy tekst → én tekst-blok.
 *
 *  TEKST VED SIDEN AF VEDHÆFTNINGER (Bjørn 27/9-2026: «min besked under det
 *  billede jeg uploaded [bliver] strippet»): serveren gemmer en upload i TO
 *  felter — `content` bærer brugerens tekst, `content_json` bærer KUN
 *  attachment-blokkene (ingen text-blok). Valget nedenfor tog derfor
 *  content_json alene, og teksten faldt væk i samme sekund serveren overtog
 *  beskeden fra den optimistiske kopi (som har BEGGE blokke, bygget i
 *  ChatView.doSend). Målt i `chat_messages` 27/9: 24 af 24 user-uploads med
 *  billede havde teksten i `content` og ingen text-blok i `content_json` —
 *  mens 376 assistent-beskeder alle havde en text-blok. Reglen rammer derfor
 *  kun uploads. Er der ALLEREDE en text-blok, røres intet, så en server der
 *  senere selv lægger teksten ind ikke dublerer den. */
export function messageToBlocks(m: { content: string; content_json?: unknown }): ContentBlock[] {
  if (Array.isArray(m.content_json) && m.content_json.length > 0) {
    const blocks = foldToolResults(m.content_json as Array<Record<string, unknown>>)
    if (typeof m.content === 'string' && m.content.trim() && !blocks.some((b) => b.type === 'text')) {
      return [{ type: 'text', text: m.content }, ...blocks]
    }
    return blocks
  }
  return stringToBlocks(m.content)
}
