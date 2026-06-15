import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { CoworkZones } from './CoworkZones'

describe('CoworkZones', () => {
  it('viser Mission Control som default og skifter til Indstillinger', () => {
    render(
      <CoworkZones
        missionControl={<div>MC-INDHOLD</div>}
        settings={<div>SETTINGS-INDHOLD</div>}
      />,
    )
    // Default = Mission Control synlig
    expect(screen.getByText('MC-INDHOLD')).toBeTruthy()
    expect(screen.queryByText('SETTINGS-INDHOLD')).toBeNull()

    // Klik på Indstillinger-rail-knappen
    fireEvent.click(screen.getByRole('button', { name: /indstillinger/i }))
    expect(screen.getByText('SETTINGS-INDHOLD')).toBeTruthy()
    expect(screen.queryByText('MC-INDHOLD')).toBeNull()
  })
})
