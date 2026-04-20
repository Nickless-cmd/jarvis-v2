import { FileText, Power, Activity, Cloud, CalendarDays } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import {
  useCognitiveSurfaces,
  SurfaceGrid,
  Section,
  KV,
  Summary,
} from './surfaces'

export function ProprioceptionTab() {
  const { surfaces, loading } = useCognitiveSurfaces()

  if (loading) {
    return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Indlæser proprioception...</div>
  }
  if (!surfaces) return <div style={s({ padding: 24, color: T.text3 })}>Ingen data</div>

  const fw = surfaces.file_watch || {}
  const ra = surfaces.reboot_awareness || {}
  const pm = surfaces.proprioception_metrics || {}
  const iw = surfaces.infra_weather || {}
  const ds = surfaces.day_shape_memory || {}

  return (
    <SurfaceGrid>
      {/* File Watch */}
      <Section icon={FileText} title="Fil-overvågning" active={fw.active}>
        <Summary text={fw.summary} />
        <KV label="Sporede filer" value={fw.tracked_files} accent />
        <KV label="Seneste ændringer" value={fw.recent_changes?.length} />
        {fw.changes_by_type_recent && Object.keys(fw.changes_by_type_recent).length ? (
          <div style={s({ marginTop: 6 })}>
            <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>Fordeling</span>
            <div style={s({ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 })}>
              {Object.entries(fw.changes_by_type_recent).map(([k, v]) => (
                <span
                  key={k}
                  style={s({
                    ...mono,
                    fontSize: 9,
                    color: T.text2,
                    background: T.bgOverlay,
                    padding: '2px 6px',
                    borderRadius: 4,
                  })}
                >
                  {k}: {v}
                </span>
              ))}
            </div>
          </div>
        ) : null}
        {Array.isArray(fw.recent_changes) && fw.recent_changes.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {fw.recent_changes.slice(0, 5).map((c, i) => (
              <div key={i} style={s({ ...mono, fontSize: 9, color: T.text2 })}>
                <span style={{ color: T.text3 }}>{String(c.when || '').slice(11, 19)}</span>{' '}
                <strong>{c.change_type}</strong>{' '}
                {c.rel_path}
              </div>
            ))}
          </div>
        ) : null}
      </Section>

      {/* Reboot Awareness */}
      <Section icon={Power} title="Genstart-bevidsthed" active={ra.active}>
        <Summary text={ra.summary} />
        <KV label="Sidste event" value={ra.last_boot_event?.kind} accent />
        <KV label="Uptime (s)" value={ra.uptime_seconds} />
        <KV label="Current PID" value={ra.current_pid} />
        <KV label="Downtime (s)" value={ra.last_boot_event?.downtime_seconds} />
        <KV label="Graceful" value={ra.last_boot_event?.graceful} />
      </Section>

      {/* Proprioception Metrics */}
      <Section icon={Activity} title="Proces-krop" active={pm.active}>
        <Summary text={pm.summary} />
        <KV label="RSS (MB)" value={pm.current?.rss_mb} accent />
        <KV label="CPU %" value={pm.current?.cpu_pct} />
        <KV label="Open FDs" value={pm.current?.open_fds} />
        <KV label="Uptime (s)" value={pm.current?.uptime_seconds} />
        <KV label="Self-latency (ms)" value={pm.current?.self_latency_ms} />
        <KV label="RSS-trend (MB)" value={pm.rss_trend_mb_over_window} />
      </Section>

      {/* Infra Weather */}
      <Section icon={Cloud} title="Infra-vejr" active={iw.active}>
        <Summary text={iw.summary} />
        <KV label="Label" value={iw.label} accent />
        <KV label="Emoji" value={iw.emoji} />
        {iw.reasons?.length ? <KV label="Kilder" value={iw.reasons} /> : null}
        <KV label="Load (0-1)" value={iw.load?.load_0_1} />
        <KV label="CPU %" value={iw.load?.cpu_pct} />
        <KV label="RAM %" value={iw.load?.ram_pct} />
        <KV label="Disk worst %" value={iw.disk?.worst_used_pct} />
        <KV label="API-cost ($)" value={iw.api_cost_today_usd} />
      </Section>

      {/* Day Shape Memory */}
      <Section icon={CalendarDays} title="Dag-form" active={ds.active}>
        <Summary text={ds.summary} />
        <KV label="I dag" value={ds.today_date} />
        <KV label="Samples i dag" value={ds.today_samples} />
        <KV label="Historik (dage)" value={ds.history_days} />
        <KV label="Anomali?" value={ds.has_anomaly_signal} accent />
        {Array.isArray(ds.today_anomalies) && ds.today_anomalies.length ? (
          <div style={s({ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 3 })}>
            {ds.today_anomalies.map((a, i) => (
              <div
                key={i}
                style={s({
                  ...mono,
                  fontSize: 9,
                  color: T.text2,
                  background: T.bgOverlay,
                  padding: '4px 6px',
                  borderRadius: 4,
                })}
              >
                {a}
              </div>
            ))}
          </div>
        ) : null}
      </Section>
    </SurfaceGrid>
  )
}
