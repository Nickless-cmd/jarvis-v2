import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const real = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return {
    ...real,
    apiFetch: vi.fn().mockResolvedValue({}),
    uploadAttachment: vi.fn(),
    getVisibleProviders: vi.fn().mockResolvedValue([
      { id: 'deepseek', models: ['deepseek-v4-flash', 'deepseek-v4-pro'] },
      { id: 'ollama', models: ['local-small'] },
    ]),
  }
})

import { Composer } from './Composer'
import { PermissionProvider } from '../../contexts/PermissionContext'
import { THINK_KEY, PROV_KEY, MODEL_KEY } from '../../lib/composerPrefs'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

function setup(isOwner = false) {
  const onSend = vi.fn()
  render(
    <PermissionProvider>
      <Composer
        streaming={false} onSend={onSend} onStop={vi.fn()} model="m"
        config={cfg} showPermissions={false} getSessionId={async () => 's1'}
        sessionId="s1" isOwner={isOwner}
      />
    </PermissionProvider>,
  )
  return { onSend }
}

function send(message: string) {
  const input = screen.getByRole('textbox')
  fireEvent.change(input, { target: { value: message } })
  fireEvent.keyDown(input, { key: 'Enter' })
}

describe('samlet model- og tænkningsvælger', () => {
  beforeEach(() => localStorage.clear())

  it('viser én vælger med aktiv model og tænkemåde', () => {
    setup()
    const picker = screen.getByRole('button', { name: 'Model og tænkning' })
    expect(picker.textContent).toContain('Standard')
    expect(picker.textContent).toContain('Automatisk')
    expect(screen.queryByRole('button', { name: 'Tænknings-effekt' })).toBeNull()
    fireEvent.click(picker)
    expect(screen.getByRole('slider', { name: 'Tænkning' })).toBeTruthy()
  })

  it('sender og husker tænkemåden, når skyderen ændres', () => {
    const { onSend } = setup()
    fireEvent.click(screen.getByRole('button', { name: 'Model og tænkning' }))
    fireEvent.change(screen.getByRole('slider', { name: 'Tænkning' }), { target: { value: '2' } })
    expect(localStorage.getItem(THINK_KEY)).toBe('deep')
    expect(screen.getByRole('button', { name: 'Model og tænkning' }).textContent).toContain('Dyb')
    send('hej')
    expect(onSend.mock.calls[0]?.[1]).toMatchObject({ thinkingMode: 'deep' })
  })

  it('vælger en model fra en anden udbyder i samme menu og sender begge valg', async () => {
    const { onSend } = setup(true)
    fireEvent.click(screen.getByRole('button', { name: 'Model og tænkning' }))
    fireEvent.click(await screen.findByRole('option', { name: 'local-small' }))
    expect(screen.getByRole('button', { name: 'Model og tænkning' }).textContent).toContain('Ollama')
    send('hej')
    expect(onSend.mock.calls[0]?.[1]).toMatchObject({ providerChoice: 'ollama', model: 'local-small' })
    expect(localStorage.getItem(PROV_KEY)).toBe('ollama')
    expect(localStorage.getItem(MODEL_KEY)).toBe('local-small')
  })
})
