import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { SidebarGreb } from './SidebarGreb'
import { BREDDE_NOEGLE, MIN_BREDDE, MAKS_BREDDE } from '../../lib/sidebarBredde'

const greb = () => screen.getByRole('separator')

/** jsdom's PointerEvent baerer ikke clientX — fireEvent.pointerMove giver
 *  derfor `undefined` og bredden falder tilbage paa standarden. En MouseEvent
 *  med typen «pointermove» har koordinaten og rammer samme lytter. Det er en
 *  begraensning i test-miljoeet, ikke i koden: en rigtig PointerEvent har
 *  clientX. */
const traekTil = (x: number) =>
  window.dispatchEvent(new MouseEvent('pointermove', { clientX: x, bubbles: true }))
const slip = () => window.dispatchEvent(new MouseEvent('pointerup', { bubbles: true }))
const bredde = () => document.documentElement.style.getPropertyValue('--sidebar-bredde')

beforeEach(() => {
  localStorage.clear()
  document.documentElement.style.removeProperty('--sidebar-bredde')
})

describe('SidebarGreb', () => {
  it('sætter den gemte bredde ved montering', () => {
    localStorage.setItem(BREDDE_NOEGLE, '340')
    render(<SidebarGreb />)
    // Sker FØR første maling, ellers ser man panelet hoppe fra standarden.
    expect(bredde()).toBe('340px')
  })

  it('træk ændrer bredden', () => {
    render(<SidebarGreb />)
    fireEvent.pointerDown(greb())
    traekTil(320)
    expect(bredde()).toBe('320px')
  })

  it('gemmer FØRST ved slip — ikke ved hver musebevægelse', () => {
    render(<SidebarGreb />)
    fireEvent.pointerDown(greb())
    traekTil(310)
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBeNull()
    slip()
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('310')
  })

  it('et træk der forlader vinduet slutter — panelet hænger ikke fast i musen', () => {
    render(<SidebarGreb />)
    fireEvent.pointerDown(greb())
    traekTil(300)
    fireEvent.blur(window)
    traekTil(500)
    expect(bredde()).toBe('300px')       // uændret efter at trækket sluttede
  })

  it('kan betjenes med TASTATUR', () => {
    // Et greb der kun kan bruges med mus lukker panelet for den der ikke
    // bruger mus — og det er en bredde, ikke en finurlighed.
    render(<SidebarGreb />)
    fireEvent.keyDown(greb(), { key: 'ArrowRight' })
    expect(bredde()).toBe('298px')       // standard 290 + 8
    fireEvent.keyDown(greb(), { key: 'ArrowLeft', shiftKey: true })
    expect(bredde()).toBe('266px')       // − 32
    fireEvent.keyDown(greb(), { key: 'Home' })
    expect(bredde()).toBe(`${MIN_BREDDE}px`)
    fireEvent.keyDown(greb(), { key: 'End' })
    expect(bredde()).toBe(`${MAKS_BREDDE}px`)
  })

  it('tastatur gemmer med det samme — der er ingen «slip»', () => {
    render(<SidebarGreb />)
    fireEvent.keyDown(greb(), { key: 'ArrowRight' })
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('298')
  })

  it('dobbeltklik nulstiller — vejen tilbage fra en helt smal kant', () => {
    localStorage.setItem(BREDDE_NOEGLE, String(MIN_BREDDE))
    render(<SidebarGreb />)
    fireEvent.doubleClick(greb())
    expect(bredde()).toBe('290px')
  })

  it('melder sine grænser til skærmlæseren', () => {
    render(<SidebarGreb />)
    expect(greb()).toHaveAttribute('aria-valuemin', String(MIN_BREDDE))
    expect(greb()).toHaveAttribute('aria-valuemax', String(MAKS_BREDDE))
  })
})
