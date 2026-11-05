import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { McpAppBlock } from './McpAppBlock'

const config = { apiBaseUrl: 'https://api.example/', authToken: 't' }

describe('McpAppBlock', () => {
  it('viser en ærlig fejl når en gammel blok mangler hostdata', async () => {
    render(<McpAppBlock block={{ attachment_id: 'a1', filename: 'app.html' }} config={config} />)
    expect(await screen.findByText(/MCP App mangler resource eller hostdata/)).toBeInTheDocument()
  })
})
