const MODES = ['chat', 'cowork', 'code'] as const
export type Mode = (typeof MODES)[number]

/** Pille-segment slider for de tre arbejds-modes (locked design). */
export function ModeSlider({ active, onChange }: { active: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className="mode-slider">
      {MODES.map((m) => (
        <button
          key={m}
          type="button"
          className={`mode-seg ${active === m ? 'active' : ''}`}
          onClick={() => onChange(m)}
        >
          {m === 'chat' ? 'Chat' : m === 'cowork' ? 'Cowork' : 'Code'}
        </button>
      ))}
    </div>
  )
}
