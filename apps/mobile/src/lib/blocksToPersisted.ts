import type { ContentBlock } from './sseProtocol'
import type { PersistedBlock } from './persistedBlocks'

/**
 * Live-blokke → den form en GEMT besked har.
 *
 * ## Hvorfor den findes
 *
 * Når en stream sluttede, blev der lagt en lokal besked med KUN teksten — og
 * `blocks` blev ryddet i samme åndedrag. Alt der levede i blokkene forsvandt
 * derfor i det sekund svaret var færdigt: tænkningen, værktøjsrækkerne,
 * resultaterne. De kom først tilbage når sessionen blev hentet igen fra
 * serveren, altså typisk ved næste app-start.
 *
 * Bjørn 12/9-2026: «tænker linjen forsvinder efter streaming, den skal persist
 * ligesom tool results». Den skulle faktisk begge dele — tool-rækkerne
 * forsvandt også, det var bare mindre synligt fordi de kom igen ved reload.
 *
 * Serveren gemmer det samme (målt: 36 thinking-blokke i 40 beskeder, og
 * 776 tool_use mod 776 tool_result). Det her er ikke en ny sandhed — det er
 * den samme, vist uden at vente på et opslag.
 *
 * ## Hvorfor tool_result bliver sin EGEN blok
 *
 * Fordi det er den form den gemte besked har, og fordi `MessageList` læser
 * dem hver for sig. En tool_use med `result` sat ville se rigtig ud i
 * reduceren og forkert i renderen.
 */
export function blocksToPersisted(blocks: ContentBlock[]): PersistedBlock[] {
  const ud: PersistedBlock[] = []
  for (const b of blocks) {
    if (!b) continue
    if (b.type === 'text') {
      if (b.text.trim()) ud.push({ type: 'text', text: b.text })
    } else if (b.type === 'thinking') {
      if (b.thinking.trim()) ud.push({ type: 'thinking', text: b.thinking })
    } else if (b.type === 'tool_use') {
      // FORELØBIGE blokke springes over. De er annonceringer af noget der
      // aldrig nåede at blive kørt færdigt i denne stream; at gemme dem ville
      // efterlade en række der snurrer for evigt i historikken.
      if (b.foreloebig) continue
      ud.push({ type: 'tool_use', name: b.name, input: b.input, tool_use_id: b.id })
      if (b.status === 'done' || b.status === 'error') {
        ud.push({
          type: 'tool_result',
          tool_use_id: b.id,
          content: b.result ?? '',
          status: b.status === 'error' ? 'error' : 'ok',
        })
      }
    }
  }
  return ud
}
