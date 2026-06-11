import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { SplitLayout } from './SplitLayout'

describe('SplitLayout', () => {
  it('viser kun main når panel er lukket', () => {
    render(<SplitLayout open={false} width={400} onResize={() => {}} panel={<div>PANEL</div>}><div>MAIN</div></SplitLayout>)
    expect(screen.getByText('MAIN')).toBeTruthy()
    expect(screen.queryByText('PANEL')).toBeNull()
  })
  it('viser både main, håndtag og panel når åbent', () => {
    render(<SplitLayout open width={400} onResize={() => {}} panel={<div>PANEL</div>}><div>MAIN</div></SplitLayout>)
    expect(screen.getByText('MAIN')).toBeTruthy()
    expect(screen.getByText('PANEL')).toBeTruthy()
    expect(screen.getByRole('separator')).toBeTruthy()
  })
})
