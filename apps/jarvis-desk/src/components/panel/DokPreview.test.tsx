import { describe, expect, it } from 'vitest'
import { render } from '@testing-library/react'
import { DokPreview } from './DokPreview'

/** Ægte render — ikke en mock af parseren.
 *
 * Baggrund: parser-testen (`lib/dokFlade.test.ts`) beviser at svaret bliver
 * TOLKET rigtigt. Den beviser ikke at det bliver VIST rigtigt. En tabel der
 * ikke er en `<table>` i DOM'en, eller en slide-liste uden numre, ville bestå
 * parser-testen og stadig være ubrugelig.
 */

function svar(v: unknown): string {
  return JSON.stringify(v)
}

describe('DokPreview — regneark', () => {
  it('rendrer en rigtig tabel med header-række og celler', () => {
    const { container } = render(
      <DokPreview dok={{
        vaerktoej: 'sheets_read',
        resultat: svar({
          status: 'ok', range: 'Ark1!A1:B3',
          values: [['Navn', 'Alder'], ['Bo', '41'], ['Ida', '29']],
        }),
      }} />,
    )
    const tabel = container.querySelector('table.dok-tabel')
    expect(tabel).not.toBeNull()
    // Første række bliver overskrift — det er læsekonventionen.
    expect(tabel!.querySelectorAll('thead th')).toHaveLength(2)
    expect(tabel!.querySelectorAll('tbody tr')).toHaveLength(2)
    expect(tabel!.querySelector('tbody tr td')!.textContent).toBe('Bo')
    expect(container.textContent).toContain('Ark1!A1:B3')
    expect(container.textContent).toContain('3 rækker')
  })
})

describe('DokPreview — dokument', () => {
  it('viser teksten med bevarede afsnit', () => {
    const { container } = render(
      <DokPreview dok={{
        vaerktoej: 'docs_read',
        resultat: svar({ status: 'ok', title: 'Notater', text: 'Første.\n\nAndet.' }),
      }} />,
    )
    const pre = container.querySelector('pre.dok-tekst')
    expect(pre).not.toBeNull()
    // Afsnittet SKAL være i teksten — ellers er det ikke et dokument, men en
    // linje. `pre-wrap` i CSS bevarer det visuelt; indholdet skal matche.
    expect(pre!.textContent).toBe('Første.\n\nAndet.')
    expect(container.textContent).toContain('Notater')
  })
})

describe('DokPreview — præsentation', () => {
  it('viser hvert slide med sit nummer', () => {
    const { container } = render(
      <DokPreview dok={{
        vaerktoej: 'slides_read',
        resultat: svar({
          status: 'ok', title: 'Kickoff', slide_count: 2,
          slides: [{ slide: 1, text: 'Velkomst' }, { slide: 2, text: 'Plan' }],
        }),
      }} />,
    )
    const slides = container.querySelectorAll('.dok-slide')
    expect(slides).toHaveLength(2)
    expect(slides[0]!.querySelector('.dok-slide-nr')!.textContent).toBe('1')
    expect(slides[0]!.querySelector('.dok-slide-tekst')!.textContent).toBe('Velkomst')
    expect(container.textContent).toContain('2 slides')
  })
})

describe('DokPreview — når svaret ikke kan læses', () => {
  it('siger det højt i stedet for at vise en tom rude', () => {
    const { container } = render(
      <DokPreview dok={{ vaerktoej: 'sheets_read', resultat: '{"status":"ok","values":[["Na' }} />,
    )
    expect(container.textContent).toContain('kunne ikke læses')
    expect(container.querySelector('table')).toBeNull()
  })

  it('viser fejl-svaret som en besked, ikke som et tomt dokument', () => {
    const { container } = render(
      <DokPreview dok={{
        vaerktoej: 'docs_read',
        resultat: svar({ status: 'error', error: 'docs_http_404' }),
      }} />,
    )
    expect(container.textContent).toContain('kunne ikke læses')
    expect(container.querySelector('pre.dok-tekst')).toBeNull()
  })
})
