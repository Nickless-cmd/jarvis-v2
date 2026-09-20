import './JarvisPulse.css'

export function JarvisPulse({ working = false, size = 18 }) {
  return <span className={`jarvis-pulse${working ? ' is-working' : ''}`} aria-hidden="true">
    <svg viewBox="0 0 100 100" width={size} height={size} fill="currentColor">
      <rect x="15" y="32" width="19" height="36" rx="9.5" />
      <rect x="41" y="19.5" width="19" height="61" rx="9.5" />
      <rect x="67" y="30.5" width="19" height="39" rx="9.5" />
    </svg>
  </span>
}
