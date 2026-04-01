export function MetricCard({ label, value, sub, color, icon: Icon, alert }) {
  return (
    <div className={`metric-card ${alert ? 'metric-card-alert' : ''}`}>
      <div className="metric-card-header">
        <span className="metric-card-label mono">{label}</span>
        {Icon && <Icon size={12} />}
      </div>
      <div className="metric-card-value" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="metric-card-sub mono">{sub}</div>}
    </div>
  )
}
