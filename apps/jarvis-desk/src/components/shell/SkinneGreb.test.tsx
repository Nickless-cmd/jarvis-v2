import { describe, it, expect, beforeEach } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { SkinneGreb } from './SkinneGreb'
import { BREDDE_NOEGLE, MAKS_BREDDE, MIN_BREDDE, STANDARD_BREDDE } from '../../lib/skinneBredde'

/** Skinnen ligger i hoejre hjoerne; grebet er dens foerste barn. */
function opsaet(bredde?: number) {
  if (bredde !== undefined) localStorage.setItem(BREDDE_NOEGLE, String(bredde))
  return render(
    <div className="code-right-stack">
      <SkinneGreb />
      <div>en rude</div>
    </div>,
  )
}

const variabel = () => document.documentElement.style.getPropertyValue('--skinne-bredde')

describe('SkinneGreb', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.style.removeProperty('--skinne-bredde')
  })

  it('saetter den gemte bredde ved mount — foer foerste maling', () => {
    // Ellers ser man skinnen hoppe fra standarden til sin egen bredde.
    opsaet(500)
    expect(variabel()).toBe('500px')
  })

  it('er en separator med tastatur', () => {
    // Et greb der kun kan bruges med mus lukker panelet for den der ikke
    // bruger mus — og det er en bredde, ikke en finurlighed.
    const greb = opsaet().getByRole('separator')
    expect(greb.getAttribute('aria-orientation')).toBe('vertical')
    expect(greb.getAttribute('tabindex')).toBe('0')
    expect(Number(greb.getAttribute('aria-valuemin'))).toBe(MIN_BREDDE)
    expect(Number(greb.getAttribute('aria-valuemax'))).toBe(MAKS_BREDDE)
  })

  it('pil-VENSTRE goer skinnen BREDERE — den vokser mod venstre', () => {
    // Modsat sidepanelet. At vende det ville vende brugerens forventning til
    // hvad pilen peger paa.
    const greb = opsaet(400).getByRole('separator')
    fireEvent.keyDown(greb, { key: 'ArrowLeft' })
    expect(variabel()).toBe('408px')
    fireEvent.keyDown(greb, { key: 'ArrowRight' })
    fireEvent.keyDown(greb, { key: 'ArrowRight' })
    expect(variabel()).toBe('392px')
  })

  it('Home og End rammer graenserne', () => {
    const greb = opsaet(400).getByRole('separator')
    fireEvent.keyDown(greb, { key: 'End' })
    expect(variabel()).toBe(`${MAKS_BREDDE}px`)
    fireEvent.keyDown(greb, { key: 'Home' })
    expect(variabel()).toBe(`${MIN_BREDDE}px`)
  })

  it('tastatur gemmer med det samme — der er intet slip at vente paa', () => {
    const greb = opsaet(400).getByRole('separator')
    fireEvent.keyDown(greb, { key: 'ArrowLeft' })
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('408')
  })

  it('et traek gemmer FOERST ved slip, ikke pr. musebevaegelse', () => {
    // Et localStorage-skriv pr. pointermove er hundredvis af skrivninger for
    // ét traek.
    const greb = opsaet(400).getByRole('separator')
    fireEvent.pointerDown(greb, { clientX: 1000 })
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('400')
    fireEvent.pointerMove(window, { clientX: 900 })
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('400')
    fireEvent.pointerUp(window)
    expect(localStorage.getItem(BREDDE_NOEGLE)).not.toBe('400')
  })

  it('dobbeltklik nulstiller', () => {
    // Har man trukket den helt smal og ikke kan ramme grebet igen, er det
    // vejen tilbage.
    const greb = opsaet(700).getByRole('separator')
    fireEvent.doubleClick(greb)
    expect(variabel()).toBe(`${STANDARD_BREDDE}px`)
  })
})
