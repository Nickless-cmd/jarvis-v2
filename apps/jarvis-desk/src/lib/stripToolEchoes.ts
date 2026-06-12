/** Fjern interne tool-resultat-markører fra synlig assistant-tekst.
 *
 *  Jarvis echoer nogen gange et tool-resultat som prosa i sit svar — fx
 *  `[list_proposals]: Pending proposals (14): …` eller de rå `[tool_result:…]`-
 *  markører. Backend-guarden fanger det og erstatter den GEMTE besked, men
 *  under live-streaming akkumulerer klienten den rå tekst. Vi spejler en
 *  best-effort oprydning ved render, så echo-linjer skjules live.
 *
 *  Konservativ: dropper KUN linjer der utvetydigt er interne markører —
 *  `[tool_result:…]`, read_tool_result-hints, og en LEDENDE `[snake_case]:`
 *  tool-echo (samme mønster som backend-guarden). Almindelig prosa røres ikke.
 */

const TOOL_RESULT_MARKER = /^\s*\[tool_result:tool-result-[a-f0-9]+\]\s*$/i
const READ_HINT = /^\s*Use read_tool_result with result_id=/i
const LEADING_TOOL_ECHO = /^\s*[([]?\s*\[[a-z_][a-z0-9_]*\]\s*:/i

export function stripToolEchoes(text: string): string {
  if (!text || (!text.includes('[tool_result:') && !text.includes('read_tool_result') && !/\[[a-z_]/.test(text))) {
    return text
  }
  const lines = text.split('\n')
  const out: string[] = []
  let leading = true // stadig i den ledende echo-zone (før første rigtige prosa)
  for (const line of lines) {
    if (TOOL_RESULT_MARKER.test(line) || READ_HINT.test(line)) continue // markør/hint: drop overalt
    if (leading && LEADING_TOOL_ECHO.test(line)) continue // ledende tool-echo: drop
    if (line.trim()) leading = false // første rigtige linje afslutter echo-zonen
    out.push(line)
  }
  return out.join('\n').replace(/^\n+/, '')
}
