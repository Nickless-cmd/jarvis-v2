import { useEffect, useRef, useState } from 'react'
import type { AppBridge as AppBridgeType } from '@modelcontextprotocol/ext-apps/app-bridge'
import type { CallToolResult, ReadResourceResult } from '@modelcontextprotocol/client'
import { callMcpAppTool, fetchBlobWithAuth, readMcpAppResource, type ApiConfig } from '../../lib/api'
import type { McpAppDescriptor } from '../../lib/sseProtocol'
import { hentWidgetNonce, medNonce } from './WidgetBlock'

const MAX_BYTES = 1024 * 1024
const MAX_HEIGHT = 100_000

export function McpAppBlock({ block, config }: {
  block: {
    attachment_id?: string
    filename?: string
    mcp_app?: McpAppDescriptor
  }
  config: ApiConfig
}) {
  const iframe = useRef<HTMLIFrameElement | null>(null)
  const [html, setHtml] = useState<string | null>(null)
  const [fejl, setFejl] = useState('')
  const [hoejde, setHoejde] = useState(320)
  const descriptor = block.mcp_app
  const attachmentId = String(block.attachment_id || '').trim()

  useEffect(() => {
    if (!attachmentId || !descriptor) {
      setFejl('MCP App mangler resource eller hostdata')
      return
    }
    let active = true
    Promise.all([
      fetchBlobWithAuth(config, `/attachments/media/${encodeURIComponent(attachmentId)}`),
      hentWidgetNonce(),
    ]).then(async ([blob, nonce]) => {
      if (blob.size > MAX_BYTES) throw new Error(`MCP App er for stor (${blob.size} B)`)
      const source = medNonce(await blob.text(), nonce)
      if (active) setHtml(source)
    }).catch((error) => {
      if (active) setFejl(String(error?.message || error))
    })
    return () => { active = false }
  }, [attachmentId, descriptor, config])

  useEffect(() => {
    const frame = iframe.current
    if (!frame || !html || !descriptor) return
    const currentFrame = frame
    const currentHtml = html
    const currentDescriptor = descriptor
    let active = true
    let bridge: AppBridgeType | null = null

    async function start() {
      if (!currentFrame.contentWindow) throw new Error('MCP App-iframe er ikke klar')
      const { AppBridge, PostMessageTransport } = await import(
        '@modelcontextprotocol/ext-apps/app-bridge'
      )
      bridge = new AppBridge(
        null,
        { name: 'jarvis-desk', version: '2' },
        { serverTools: {}, serverResources: {} },
        { hostContext: {
          theme: document.documentElement.dataset.theme === 'light' ? 'light' : 'dark',
          displayMode: 'inline',
          platform: typeof (window as Window & { jarvisDesk?: unknown }).jarvisDesk === 'object'
            ? 'desktop' : 'web',
          locale: navigator.language,
          timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        } },
      )
      bridge.oncalltool = async (params) => (
        await callMcpAppTool(
          config,
          currentDescriptor.server,
          params.name,
          (params.arguments || {}) as Record<string, unknown>,
        )
      ) as unknown as CallToolResult
      bridge.onreadresource = async (params) => (
        await readMcpAppResource(config, currentDescriptor.server, params.uri)
      ) as unknown as ReadResourceResult
      bridge.addEventListener('sizechange', ({ height }) => {
        if (!active || height == null || !Number.isFinite(height) || height < 48) return
        setHoejde(Math.min(Math.round(height), MAX_HEIGHT))
      })
      bridge.addEventListener('initialized', () => {
        if (!active || !bridge) return
        void bridge.sendToolInput({ arguments: currentDescriptor.arguments })
          .then(() => bridge?.sendToolResult(currentDescriptor.result as unknown as CallToolResult))
          .catch((error) => setFejl(String(error?.message || error)))
      })
      const transport = new PostMessageTransport(
        currentFrame.contentWindow,
        currentFrame.contentWindow,
      )
      await bridge.connect(transport)
      // Listeneren er nu sat op. Først NU må appens scripts starte, ellers kan
      // dens initialize-besked nå at passere før hosten lytter.
      currentFrame.srcdoc = currentHtml
    }

    void start().catch((error) => {
      if (active) setFejl(String(error?.message || error))
    })
    return () => {
      active = false
      if (bridge) {
        const currentBridge = bridge
        void Promise.race([
          currentBridge.teardownResource({}),
          new Promise((resolve) => window.setTimeout(resolve, 250)),
        ]).catch(() => undefined).finally(() => {
          void currentBridge.close().catch(() => undefined)
        })
      }
    }
  }, [html, descriptor, config])

  if (fejl) return <div className="rv-kort rv-widget-fejl">MCP App kunne ikke vises: {fejl}</div>
  if (!html) return <div className="rv-kort rv-widget-venter">MCP App hentes…</div>
  return (
    <iframe
      ref={iframe}
      className="rv-widget rv-mcp-app"
      title={block.filename || 'MCP App'}
      sandbox="allow-scripts"
      referrerPolicy="no-referrer"
      style={{ width: '100%', height: hoejde, border: 0, display: 'block' }}
    />
  )
}
