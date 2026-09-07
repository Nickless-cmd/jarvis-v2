import { planlaegPreview, INLINE_MAKS_BYTES } from './filePreview'

it('billeder bliver billeder — også ud fra mime alene', () => {
  expect(planlaegPreview('foto.png').slags).toBe('billede')
  expect(planlaegPreview('uden-endelse', 'image/jpeg').slags).toBe('billede')
})

it('PDF overlades til telefonens egen fremviser', () => {
  const p = planlaegPreview('rapport.pdf')
  expect(p.slags).toBe('system')
  expect(p.etiket).toBe('PDF')
})

it('kode vises inline MED sprog til farvning', () => {
  expect(planlaegPreview('a.py')).toMatchObject({ slags: 'inline', sprog: 'python', etiket: 'Python' })
  expect(planlaegPreview('b.tsx').sprog).toBe('tsx')
})

it('almindelig tekst vises inline uden sprog', () => {
  expect(planlaegPreview('noter.md')).toMatchObject({ slags: 'inline', sprog: '', etiket: 'Markdown' })
  expect(planlaegPreview('x', 'text/plain').slags).toBe('inline')
})

it('en stor tekstfil vises IKKE inline — man læser ikke en megabyte i en boble', () => {
  expect(planlaegPreview('kæmpe.log', '', INLINE_MAKS_BYTES + 1).slags).toBe('system')
  expect(planlaegPreview('kæmpe.log', '', INLINE_MAKS_BYTES + 1).etiket).toBe('Log')
  expect(planlaegPreview('lille.log', '', 100).slags).toBe('inline')
})

it('Dockerfile uden endelse genkendes', () => {
  expect(planlaegPreview('Dockerfile')).toMatchObject({ slags: 'inline', sprog: 'dockerfile' })
})

it('ukendt type får systemet og en ærlig etiket', () => {
  expect(planlaegPreview('ting.xyz')).toMatchObject({ slags: 'system', etiket: 'XYZ' })
  expect(planlaegPreview('uden')).toMatchObject({ slags: 'system', etiket: 'Fil' })
})

it('kontor- og arkivfiler navngives så man ved hvad man åbner', () => {
  expect(planlaegPreview('a.docx').etiket).toBe('Word')
  expect(planlaegPreview('b.zip').etiket).toBe('Arkiv')
  expect(planlaegPreview('c.mp4').etiket).toBe('Video')
})
