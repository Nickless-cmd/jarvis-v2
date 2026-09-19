import { describe, expect, it, vi } from 'vitest'
import { render } from '@testing-library/react'
import { CategoryPage, CategorySection } from './CategoryPage'

describe('CategoryPage', () => {
  it('fører gamle panelgenveje til den tilsvarende sektion', () => {
    const scroll = vi.fn()
    HTMLElement.prototype.scrollIntoView = scroll
    render(
      <CategoryPage title="Konto og sikkerhed" description="Din konto" focusSection="privacy">
        <CategorySection id="konto" title="Profil"><div>Profilindhold</div></CategorySection>
        <CategorySection id="privacy" title="Privatliv"><div>Privatlivsindhold</div></CategorySection>
      </CategoryPage>,
    )
    expect(scroll).toHaveBeenCalledTimes(1)
    expect(document.querySelector('[data-section="privacy"]')).toBeTruthy()
  })
})
