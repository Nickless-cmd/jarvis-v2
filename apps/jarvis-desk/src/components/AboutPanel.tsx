import pkg from '../../package.json'

/** Om / system-info (§5.2). Statisk overblik: version, server, rolle, model.
 *  Version importeres ved build (resolveJsonModule) — ingen Electron-plumbing. */
export function AboutPanel({
  apiBaseUrl,
  role,
  model,
}: {
  apiBaseUrl?: string
  role?: string
  model?: string
}) {
  return (
    <section className="about-panel">
      <h3>Om</h3>
      <table className="about-table">
        <tbody>
          <tr><td>App</td><td>J.A.R.V.I.S. Desktop</td></tr>
          <tr><td>Version</td><td>{pkg.version}</td></tr>
          <tr><td>Server</td><td>{apiBaseUrl || '–'}</td></tr>
          <tr><td>Rolle</td><td>{role || '–'}</td></tr>
          <tr><td>Default-model</td><td>{model || '–'}</td></tr>
        </tbody>
      </table>
      <p className="about-note">
        Bygget på /chat/stream/v2 (Anthropic-stil protokol). Lokal-først, privatlivs-først.
      </p>
    </section>
  )
}
