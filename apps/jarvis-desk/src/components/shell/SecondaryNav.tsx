import { Settings } from 'lucide-react'

export type SecondarySurface = 'memory' | 'scheduling' | 'settings'

/** Sekundær nav i sidebar-foden ved bruger-avataren.
 *
 *  Hukommelse og Planlagt blev taget ud 8/9-2026. To ikoner i foden for flader
 *  man slår op i sjældent er dyr plads — og de er IKKE utilgængelige: begge
 *  ligger i Ctrl+K-paletten (`surface:memory`, `surface:scheduling`), hvor man
 *  leder efter dem når man endelig skal bruge dem. Typen beholder navnene, saa
 *  paletten og ruterne i App.tsx virker uændret. */
export function SecondaryNav({
  active,
  onSelect,
}: {
  active: string
  onSelect: (s: SecondarySurface) => void
}) {
  const items: Array<{ key: SecondarySurface; icon: typeof Settings; title: string }> = [
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
