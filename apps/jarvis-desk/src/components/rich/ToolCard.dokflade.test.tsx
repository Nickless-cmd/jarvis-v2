import { describe, expect, it } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useContext } from 'react'
import { ToolCard } from './ToolCard'
import { PanelProvider, PanelContext } from '../../contexts/PanelContext'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Øje-knappen på et Google-læser-svar.
 *
 * Baggrund (27/10-2026): fladen `DokPreview` kan rendere et regneark, et
 * dokument og en præsentation — men hvis knappen der ÅBNER den ikke vises,
 * findes fladen ikke i praksis. Denne test måler forbindelsen, ikke
 * komponenten: vises knappen, og åbner den det rigtige mål?
 */

type Blok = Extract<ContentBlock, { type: 'tool_use' }>

function blok(over: Partial<Blok>): Blok {
  return { type: 'tool_use', id: 't1', name: 'sheets_read', input: {}, status: 'done', ...over }
}

/** Læser panelets mål ud, så testen kan se HVAD knappen åbnede. */
function Probe() {
  const panel = useContext(PanelContext)
  const t = panel?.target
  return <div data-testid="maal">{t ? JSON.stringify(t) : 'intet'}</div>
}

function medPanel(ui: React.ReactNode) {
  return render(<PanelProvider defaultWidth={400}>{ui}<Probe /></PanelProvider>)
}

describe('ToolCard — øje-knap til dok-fladen', () => {
  it('vises på et færdigt sheets_read-svar', () => {
    medPanel(<ToolCard block={blok({ name: 'sheets_read', result: '{"status":"ok"}' })} density="compact" />)
    expect(screen.getByLabelText(/se .* i panelet/i)).toBeInTheDocument()
  })

  it('vises på docs_read og slides_read', () => {
    for (const navn of ['docs_read', 'slides_read']) {
      const { unmount } = medPanel(
        <ToolCard block={blok({ name: navn, result: '{"status":"ok"}' })} density="compact" />,
      )
      expect(screen.getByLabelText(/se .* i panelet/i)).toBeInTheDocument()
      unmount()
    }
  })

  it('vises IKKE på værktøjer uden en flade', () => {
    // drive_search giver en filliste, ikke et dokument. En øje-knap der
    // åbnede et panel uden indhold ville være værre end ingen knap.
    for (const navn of ['drive_search', 'drive_download', 'docs_append', 'bash']) {
      const { unmount } = medPanel(
        <ToolCard block={blok({ name: navn, result: '{"status":"ok"}' })} density="compact" />,
      )
      expect(screen.queryByLabelText(/se .* i panelet/i)).toBeNull()
      unmount()
    }
  })

  it('vises IKKE mens kaldet stadig kører', () => {
    medPanel(<ToolCard block={blok({ name: 'sheets_read', status: 'running' })} density="compact" />)
    expect(screen.queryByLabelText(/se .* i panelet/i)).toBeNull()
  })

  it('åbner panelet med værktøjsnavn og det fulde svar ved klik', () => {
    const raat = '{"status":"ok","range":"A1:B2","values":[["Navn","Alder"],["Bo","41"]]}'
    medPanel(<ToolCard block={blok({ name: 'sheets_read', result: raat })} density="compact" />)
    fireEvent.click(screen.getByLabelText(/se .* i panelet/i))
    const maal = JSON.parse(screen.getByTestId('maal').textContent || '{}')
    expect(maal.type).toBe('dok')
    expect(maal.dok.vaerktoej).toBe('sheets_read')
    // Svaret skal videre UÆNDRET — panelet tolker det selv.
    expect(maal.dok.resultat).toBe(raat)
  })
})
