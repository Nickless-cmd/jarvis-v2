/** Tastaturgenveje — gør genvejene synlige/opdagelige (analyse §14.2).
 *  Statisk liste; holdes i sync med GlobalShortcuts + composerens Enter-send. */
const SHORTCUTS: { keys: string; desc: string }[] = [
  { keys: 'Enter', desc: 'Send besked' },
  { keys: 'Shift+Enter', desc: 'Ny linje' },
  { keys: 'Esc', desc: 'Stop igangværende svar' },
  { keys: 'Ctrl/Cmd + ,', desc: 'Åbn indstillinger' },
  { keys: 'Ctrl/Cmd + K', desc: 'Søg i samtaler' },
]

export function KeyboardHelpPanel() {
  return (
    <section className="kbd-help">
      <h3>Tastaturgenveje</h3>
      <table className="kbd-help-table">
        <tbody>
          {SHORTCUTS.map((s) => (
            <tr key={s.keys}>
              <td><kbd>{s.keys}</kbd></td>
              <td>{s.desc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}
