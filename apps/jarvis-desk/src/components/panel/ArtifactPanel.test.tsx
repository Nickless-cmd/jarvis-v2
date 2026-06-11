import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ArtifactPanel } from './ArtifactPanel'

describe('ArtifactPanel', () => {
  it('viser titel + markdown-indhold', () => {
    render(<ArtifactPanel artifact={{ kind: 'markdown', title: 'Min Spec', content: '# Overskrift' }} onClose={() => {}} />)
    expect(screen.getByText('Min Spec')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Overskrift' })).toBeTruthy()
  })
  it('kalder onClose når luk klikkes', () => {
    const onClose = vi.fn()
    render(<ArtifactPanel artifact={{ kind: 'code', title: 'a.js', language: 'js', content: 'const x=1' }} onClose={onClose} />)
    screen.getByLabelText('Luk panel').click()
    expect(onClose).toHaveBeenCalled()
  })
})
