import { useConnection } from '../../hooks/useConnection'

/** Forbindelses-status i header-højre: grøn/rød dot + host + ping-ms. */
export function ConnectionPill({ config }: { config: { apiBaseUrl: string; authToken: string | null } }) {
  const { online, latencyMs, host } = useConnection(config)
  return (
    <div className={`connection-pill ${online ? 'online' : 'offline'}`} title={config.apiBaseUrl}>
      <span className="connection-dot" />
      <span className="connection-host">{host}</span>
      {online && latencyMs !== null && <span className="connection-ping">{latencyMs} ms</span>}
      {!online && <span className="connection-ping">offline</span>}
    </div>
  )
}
