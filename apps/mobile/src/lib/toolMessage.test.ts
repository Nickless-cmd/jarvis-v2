import { parseToolMessage, toolPreview } from './toolMessage'

it('parser tool_result-prefix + bash', () => {
  const r = parseToolMessage('[tool_result:tool-result-26c4] [bash]: cde1c3f3 (HEAD -> main)')
  expect(r.tool).toBe('bash')
  expect(r.body).toBe('cde1c3f3 (HEAD -> main)')
})

it('parser uden tool_result-prefix', () => {
  const r = parseToolMessage('[gmail_list] [Tool gmail_list returned 4509 chars]')
  expect(r.tool).toBe('gmail_list')
  expect(r.body).toBe('[Tool gmail_list returned 4509 chars]')
})

it('falder tilbage til generisk navn', () => {
  const r = parseToolMessage('bare noget tekst uden klammer')
  expect(r.tool).toBe('værktøj')
  expect(r.body).toBe('bare noget tekst uden klammer')
})

it('toolPreview trunkerer + samler whitespace', () => {
  expect(toolPreview('a\n\nb   c')).toBe('a b c')
  expect(toolPreview('x'.repeat(200)).endsWith('…')).toBe(true)
})
