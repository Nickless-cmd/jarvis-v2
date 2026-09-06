import { buildArtifactPreview } from './artifactPreview'

it('recognizes diffs and returns a short preview body', () => {
  const p = buildArtifactPreview({ kind: 'patch', detail: 'diff --git a/a.ts b/a.ts\n+hello\n-world' })
  expect(p.kind).toBe('diff')
  expect(p.title).toBe('Diff')
  expect(p.body).toContain('+hello')
})

it('recognizes markdown and html content', () => {
  expect(buildArtifactPreview({ kind: 'document', detail: '# Plan\n\nTekst' }).kind).toBe('markdown')
  expect(buildArtifactPreview({ kind: 'html', detail: '<main>Hej</main>' }).kind).toBe('html')
})
