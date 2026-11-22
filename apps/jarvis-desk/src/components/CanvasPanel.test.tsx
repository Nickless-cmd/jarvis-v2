import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CanvasPanel } from './CanvasPanel'
import { onCanvasSend, canvasBesked } from '../lib/canvasBus'

describe('CanvasPanel', () => {
  let af: (() => void) | null = null
  afterEach(() => { af?.(); af = null })

  it('sender den rettede tekst tilbage til samtalen', () => {
    const modtaget = vi.fn()
    af = onCanvasSend(modtaget)
    render(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} />)
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'v2' } })
    fireEvent.click(screen.getByText('Send til samtalen'))
    expect(modtaget).toHaveBeenCalledWith({ titel: 'Plan', tekst: 'v2' })
    expect(canvasBesked({ titel: 'Plan', tekst: 'v2' })).toContain('v2')
  })

  it('siger det højt når ingen samtale lytter', () => {
    render(<CanvasPanel canvas={{ titel: 'Plan', tekst: 'v1' }} />)
    fireEvent.click(screen.getByText('Send til samtalen'))
    expect(screen.getByRole('alert').textContent).toContain('intet blev sendt')
  })
})
