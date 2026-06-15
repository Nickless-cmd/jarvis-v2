import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getAccountApps = vi.fn()
const getAccountMcp = vi.fn()
const addMcpServer = vi.fn().mockResolvedValue(undefined)
const removeMcpServer = vi.fn().mockResolvedValue(undefined)
vi.mock('../../lib/coworkApi', () => ({
  getAccountApps: (...a: unknown[]) => getAccountApps(...a),
  getAccountMcp: (...a: unknown[]) => getAccountMcp(...a),
  addMcpServer: (...a: unknown[]) => addMcpServer(...a),
  removeMcpServer: (...a: unknown[]) => removeMcpServer(...a),
}))

import { AppsSection } from './AppsSection'
import { McpSection } from './McpSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('AppsSection', () => {
  beforeEach(() => getAccountApps.mockReset())
  it('viser connectede apps', async () => {
    getAccountApps.mockResolvedValue([{ plugin_id: 'gmail', name: 'Gmail', status: 'connected', detail: '' }])
    render(<AppsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('Gmail')).toBeTruthy())
    expect(screen.getByText('connected')).toBeTruthy()
  })
  it('viser tom-tilstand', async () => {
    getAccountApps.mockResolvedValue([])
    render(<AppsSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/ingen connectede apps/i)).toBeTruthy())
  })
})

describe('McpSection', () => {
  beforeEach(() => { getAccountMcp.mockReset(); addMcpServer.mockClear() })
  it('tilføjer en MCP-server', async () => {
    getAccountMcp.mockResolvedValue([])
    render(<McpSection config={cfg} />)
    await screen.findByText(/ingen mcp-servere/i)
    fireEvent.change(screen.getByPlaceholderText(/navn/i), { target: { value: 'CF' } })
    fireEvent.change(screen.getByPlaceholderText(/url/i), { target: { value: 'https://x' } })
    fireEvent.click(screen.getByRole('button', { name: /tilføj/i }))
    await waitFor(() => expect(addMcpServer).toHaveBeenCalledWith(cfg, 'CF', 'https://x'))
  })
})
