import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { EditedFilesCard } from './EditedFilesCard'

const FILER = [{ path: 'apps/x/ChangesPanel.tsx', gange: 1 }, { path: 'apps/x/ChangesPanel.test.tsx', gange: 1 }]

describe('EditedFilesCard', () => {
  it('siger hvor mange filer — og viser dem', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} />)
    expect(screen.getByText('Redigerede 2 filer')).toBeInTheDocument()
    expect(screen.getByText('x/ChangesPanel.tsx')).toBeInTheDocument()
  })

  it('bøjer ental rigtigt', () => {
    render(<EditedFilesCard filer={[FILER[0]!]} onAabn={() => {}} />)
    expect(screen.getByText('Redigerede 1 fil')).toBeInTheDocument()
  })

  it('viser INTET når der ikke er redigeret noget', () => {
    const { container } = render(<EditedFilesCard filer={[]} onAabn={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('klik på en fil åbner NETOP den fil', () => {
    const aabn = vi.fn()
    render(<EditedFilesCard filer={FILER} onAabn={aabn} />)
    fireEvent.click(screen.getByText('x/ChangesPanel.test.tsx'))
    expect(aabn).toHaveBeenCalledWith('apps/x/ChangesPanel.test.tsx')
  })

  it('«Vis ændringer» åbner ruden på den første fil', () => {
    const aabn = vi.fn()
    render(<EditedFilesCard filer={FILER} onAabn={aabn} />)
    fireEvent.click(screen.getByRole('button', { name: 'Vis ændringer' }))
    expect(aabn).toHaveBeenCalledWith('apps/x/ChangesPanel.tsx')
  })

  it('tallene vises når de KENDES', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}}
      tal={{ 'apps/x/ChangesPanel.tsx': { added: 166, removed: 0 } }} />)
    expect(screen.getByText('+166')).toBeInTheDocument()
  })

  it('en fil UDEN kendte tal får ikke «+0 −0»', () => {
    // Tallene kommer fra værktøjets resultat. Mangler de, ville 0 være et gæt.
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} tal={{}} />)
    expect(screen.queryByText('+0')).not.toBeInTheDocument()
  })

  it('en fil rettet flere gange er ÉN række — men antallet siges', () => {
    render(<EditedFilesCard filer={[{ path: 'a.ts', gange: 3 }]} onAabn={() => {}} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('3×')).toBeInTheDocument()
  })

  it('viser tre filer først og kan folde resten ud', () => {
    const filer = Array.from({ length: 5 }, (_, i) => ({ path: `src/fil-${i}.ts`, gange: 1 }))
    render(<EditedFilesCard filer={filer} onAabn={() => {}} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: 'Vis 2 filer mere' }))
    expect(screen.getAllByRole('listitem')).toHaveLength(5)
  })

  it('summerer kun kendte per-fil-tal i overskriften', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} tal={{
      'apps/x/ChangesPanel.tsx': { added: 9, removed: 4 },
      'apps/x/ChangesPanel.test.tsx': { added: 3, removed: 1 },
    }} />)
    expect(document.querySelector('.edited-files-head')).toHaveTextContent('+12')
    expect(document.querySelector('.edited-files-head')).toHaveTextContent('−5')
  })
})
