// Parser tool-beskeder til pæne kort. Backend leverer tool-output som rå
// strenge i formen "[tool_result:ID] [toolnavn]: <body>" eller
// "[toolnavn] [Tool toolnavn returned …]". Vi udtrækker værktøjsnavn + body
// så de kan vises som kort i stedet for rå tekst.

export interface ParsedTool {
  tool: string
  body: string
}

const RESULT_PREFIX = /^\s*\[tool_result:[^\]]*\]\s*/i

export function parseToolMessage(content: string): ParsedTool {
  const raw = (content ?? '').replace(RESULT_PREFIX, '').trim()
  const m = raw.match(/^\[([^\]]+)\]:?\s*([\s\S]*)$/)
  if (m) {
    return { tool: m[1]!.trim(), body: m[2]!.trim() }
  }
  return { tool: 'værktøj', body: raw }
}

/** Kort etiket til kortets header (fjerner "Tool …"-støj fra body-preview). */
export function toolPreview(body: string, max = 140): string {
  const oneLine = body.replace(/\s+/g, ' ').trim()
  return oneLine.length > max ? `${oneLine.slice(0, max)}…` : oneLine
}
