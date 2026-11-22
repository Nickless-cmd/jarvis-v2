import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HooksSection } from './HooksSection'
import { getToolHookLog, getToolHooks, reloadToolHooks } from '../../lib/toolHooksApi'

vi.mock('../../lib/toolHooksApi', () => ({
  getToolHooks: vi.fn(),
  getToolHookLog: vi.fn(),
  reloadToolHooks: vi.fn(),
}))

const config = { apiBaseUrl: 'http://x', authToken: 'token' }

describe('HooksSection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getToolHooks).mockResolvedValue({
      enabled: false,
      config: '/runtime/tool_hooks.json',
      config_findes: false,
      hooks: [{ name: 'audit', match: '.*', before: false, after: true, timeout_s: 5, active: true }],
      log: { path: '/runtime/tool_hooks.jsonl', exists: true, size_bytes: 2048, rotated: true, rotated_path: '/runtime/tool_hooks.jsonl.1' },
    })
    vi.mocked(getToolHookLog).mockResolvedValue({
      entries: [{ time: '2026-11-22T10:00:00Z', tool: 'bash', phase: 'after', result: 'ok' }],
      coverage_24h: { confined: 0, fail_open: 3, non_shell: 2 },
      invalid_lines: 0,
      log: { path: '/runtime/tool_hooks.jsonl', exists: true, size_bytes: 2048, rotated: true, rotated_path: '/runtime/tool_hooks.jsonl.1' },
    })
    vi.mocked(reloadToolHooks).mockResolvedValue({
      enabled: true, config: '/runtime/tool_hooks.json', config_findes: true, hooks: [],
      log: { path: '/runtime/tool_hooks.jsonl', exists: true, size_bytes: 2048, rotated: true, rotated_path: '/runtime/tool_hooks.jsonl.1' },
    })
  })

  it('viser hook-status, log og den ærlige sandbox-dækning', async () => {
    render(<HooksSection config={config} />)

    expect(await screen.findByRole('alert')).toHaveTextContent(/config.*mangler/i)
    expect(screen.getByText('audit')).toBeTruthy()
    expect(screen.getByText('.*')).toBeTruthy()
    expect(screen.getByText(/0 indespærret/i)).toBeTruthy()
    expect(screen.getByText(/3 fail-open/i)).toBeTruthy()
    expect(screen.getByText(/2,0 KB/i)).toBeTruthy()
    expect(screen.getByText(/roteret/i)).toBeTruthy()
    expect(screen.getByRole('cell', { name: 'bash' })).toBeTruthy()
  })

  it('genindlæser konfigurationen ved brugerens klik', async () => {
    render(<HooksSection config={config} />)
    fireEvent.click(await screen.findByRole('button', { name: /genindlæs/i }))
    await waitFor(() => expect(reloadToolHooks).toHaveBeenCalledWith(config))
    await waitFor(() => expect(getToolHooks).toHaveBeenCalledTimes(2))
  })
})
