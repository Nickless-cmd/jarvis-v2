import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { act } from 'react'
import { CoworkZones } from './CoworkZones'
import { emitZone } from '../../lib/coworkZone'

describe('CoworkZones', () => {
  it('har ingen intern rail (ét panel — zone styres fra Sidebar)', () => {
    const { container } = render(<CoworkZones>{(z) => <div>{z}</div>}</CoworkZones>)
    expect(container.querySelector('.cowork-rail')).toBeNull()
  })

  it('viser mc-zonen som default', () => {
    const { getByText } = render(<CoworkZones>{(z) => <div>zone:{z}</div>}</CoworkZones>)
    expect(getByText('zone:mc')).toBeInTheDocument()
  })

  it('skifter zone når emitZone kaldes', () => {
    const { getByText } = render(<CoworkZones>{(z) => <div>zone:{z}</div>}</CoworkZones>)
    act(() => emitZone('marketplace'))
    expect(getByText('zone:marketplace')).toBeInTheDocument()
  })
})
