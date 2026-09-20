import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { FigurKrop } from './FigurKrop'
import { ThemeSection } from '../components/settings/ThemeSection'

/**
 * Figurens udseende (20/9-2026). Bjørn valgte at beholde ansigtet OG tilføje
 * Puls som et skin man kan skifte til i Udseende — derfor to ting at holde
 * fast: at det ene ikke spiser det andet, og at valget slår igennem straks.
 */
describe('figurens udseende — kroppen', () => {
  it('ansigtet er kroppen når intet er valgt', () => {
    const { container } = render(<FigurKrop handling="hvile" ring="rolig" laener={null} />)
    expect(container.querySelector('.figur-ansigt')).not.toBeNull()
    expect(container.querySelector('.figur-puls-bjaelker')).toBeNull()
  })

  it('puls tegner mærket — tre bjælker, og intet ansigt', () => {
    const { container } = render(<FigurKrop handling="hvile" ring="rolig" laener={null} skin="puls" />)
    expect(container.querySelectorAll('.figur-puls-bjaelker rect')).toHaveLength(3)
    expect(container.querySelector('.figur-ansigt')).toBeNull()
    expect(container.querySelector('.figur-oejne')).toBeNull()
    expect(container.querySelector('.figur-krop')?.className).toContain('skin-puls')
  })

  it('puls slår hurtigere mens han arbejder', () => {
    const rolig = render(<FigurKrop handling="hvile" ring="rolig" laener={null} skin="puls" />)
    expect(rolig.container.querySelector('.figur-puls-bjaelker.slaa-hurtigt')).toBeNull()
    const hurtig = render(<FigurKrop handling="arbejder" ring="hurtig" laener={null} skin="puls" />)
    expect(hurtig.container.querySelector('.figur-puls-bjaelker.slaa-hurtigt')).not.toBeNull()
  })

  it('gløden er fælles — begge kroppe ånder', () => {
    const ansigt = render(<FigurKrop handling="hvile" ring="rolig" laener={null} />)
    expect(ansigt.container.querySelector('.figur-glød')).not.toBeNull()
    const puls = render(<FigurKrop handling="hvile" ring="rolig" laener={null} skin="puls" />)
    expect(puls.container.querySelector('.figur-glød')).not.toBeNull()
  })
})

describe('udseende-valget i Udseende', () => {
  let skin: 'ansigt' | 'puls' = 'ansigt'
  const bro = {
    figur: {
      vist: vi.fn(async () => true),
      saetVist: vi.fn(async (v: boolean) => v),
      skin: vi.fn(async () => skin),
      saetSkin: vi.fn(async (s: 'ansigt' | 'puls') => { skin = s; return s }),
    },
  }
  beforeEach(() => {
    skin = 'ansigt'
    bro.figur.saetSkin.mockClear()
    ;(window as unknown as { jarvisDesk: typeof bro }).jarvisDesk = bro
  })
  afterEach(() => { delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk })

  it('vælgeren viser begge kroppe, og skiftet registreres', async () => {
    render(<ThemeSection />)
    const puls = await screen.findByRole('button', { name: 'Puls' })
    expect(screen.getByRole('button', { name: 'Ansigtet' })).toBeTruthy()
    fireEvent.click(puls)
    await waitFor(() => expect(bro.figur.saetSkin).toHaveBeenCalledWith('puls'))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Puls' }).className).toContain('active'))
  })

  it('i en browser-fane (ingen desk) tegnes ingen vælger', () => {
    delete (window as unknown as { jarvisDesk?: unknown }).jarvisDesk
    render(<ThemeSection />)
    expect(screen.queryByRole('button', { name: 'Puls' })).toBeNull()
  })
})
