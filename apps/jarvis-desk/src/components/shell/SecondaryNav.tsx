import { Brain, Clock, Settings } from 'lucide-react'

export type SecondarySurface = 'memory' | 'scheduling' | 'settings'

/** Sekundær nav (opslags-flader) i sidebar-foden ved bruger-avataren. */
export function SecondaryNav({
  active,
  onSelect,
}: {
  active: string
  onSelect: (s: SecondarySurface) => void
}) {
  const items: Array<{ key: SecondarySurface; icon: typeof Brain; title: string }> = [
    { key: 'memory', icon: Brain, title: 'Memory' },
    { key: 'scheduling', icon: Clock, title: 'Scheduling' },
    { key: 'settings', icon: Settings, title: 'Indstillinger' },
  ]
  return (
    <div className="secondary-nav">
      {items.map(({ key, icon: Icon, title }) => (
        <button
          key={key}
          type="button"
          className={`icon-btn ${active === key ? 'active' : ''}`}
          title={title}
          onClick={() => onSelect(key)}
        >
          <Icon size={14} />
        </button>
      ))}
    </div>
  )
}
