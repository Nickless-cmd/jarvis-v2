export type ArtifactPreviewKind = 'diff' | 'markdown' | 'html' | 'text'

export interface ArtifactPreviewInput {
  kind?: string
  detail?: string
  content?: string
}

export interface ArtifactPreview {
  kind: ArtifactPreviewKind
  title: string
  body: string
}

function compact(text: string): string {
  return text.replace(/\n{3,}/g, '\n\n').trim().slice(0, 1200)
}

export function buildArtifactPreview(input: ArtifactPreviewInput): ArtifactPreview {
  const text = compact(String(input.content ?? input.detail ?? ''))
  const lowerKind = String(input.kind ?? '').toLowerCase()
  if (lowerKind.includes('patch') || /^diff --git/m.test(text) || /^[+-][^\n]/m.test(text)) {
    return { kind: 'diff', title: 'Diff', body: text || 'Ingen diff-preview.' }
  }
  if (lowerKind.includes('html') || /<\/?[a-z][\s\S]*>/i.test(text)) {
    return { kind: 'html', title: 'HTML', body: text || 'Ingen HTML-preview.' }
  }
  if (lowerKind.includes('markdown') || /^#{1,3}\s+/m.test(text) || /\*\*[^*]+\*\*/.test(text)) {
    return { kind: 'markdown', title: 'Markdown', body: text || 'Ingen markdown-preview.' }
  }
  return { kind: 'text', title: 'Tekst', body: text || 'Ingen preview.' }
}
