import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, within } from '@testing-library/react'

vi.mock('../../lib/api', async () => {
  const real = await vi.importActual<Record<string, unknown>>('../../lib/api')
  return {
    ...real,
    apiFetch: vi.fn().mockResolvedValue({}),
    uploadAttachment: vi.fn(),
    getVisibleProviders: vi.fn().mockResolvedValue([
      { id: 'deepseek', models: ['deepseek-v4-flash', 'deepseek-v4-pro'] },
      { id: 'ollama', models: ['local-small', 'local-1', 'local-2', 'local-3', 'local-4', 'local-5', 'local-6', 'local-7', 'local-8', 'local-9'] },
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
    expect(picker.textContent).toContain('Auto')
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
    expect(await screen.findByRole('option', { name: 'V4 Flash' })).toBeTruthy()
    expect(screen.queryByRole('option', { name: 'local-small' })).toBeNull()
    fireEvent.change(screen.getByRole('combobox', { name: 'Udbyder' }), { target: { value: 'ollama' } })
    expect(screen.queryByRole('option', { name: 'V4 Flash' })).toBeNull()
    expect(within(screen.getByRole('listbox', { name: 'Modeller' })).getAllByRole('option').length).toBeLessThanOrEqual(7)
    fireEvent.change(screen.getByRole('searchbox', { name: 'Find model' }), { target: { value: 'local-9' } })
    fireEvent.click(screen.getByRole('option', { name: 'local-9' }))
    expect(screen.getByRole('button', { name: 'Model og tænkning' }).textContent).toContain('local-9')
    send('hej')
    expect(onSend.mock.calls[0]?.[1]).toMatchObject({ providerChoice: 'ollama', model: 'local-9' })
    expect(localStorage.getItem(PROV_KEY)).toBe('ollama')
    expect(localStorage.getItem(MODEL_KEY)).toBe('local-9')
  })

  it('holder knapteksten kort, men viser fuldt valg som tooltip', () => {
    localStorage.setItem(PROV_KEY, 'deepseek')
    localStorage.setItem(MODEL_KEY, 'deepseek-v4-flash')
    setup(true)
    const picker = screen.getByRole('button', { name: 'Model og tænkning' })
    expect(picker.textContent).toMatch(/V4 Flash.*Auto/)
    expect(picker.textContent).not.toContain('Deepseek')
    expect(picker.title).toContain('Deepseek · V4 Flash · Automatisk')
  })
})
