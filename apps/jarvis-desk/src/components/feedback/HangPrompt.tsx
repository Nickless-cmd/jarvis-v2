/** R2: watchdog 90s uden event. Brugeren beslutter genoptag (ny tur) eller
 *  afbryd (server-cancel). */
export function HangPrompt({ onResume, onAbort }: { onResume: () => void; onAbort: () => void }) {
  return (
    <div className="banner banner-warn">
      Jarvis svarer ikke.{' '}
      <button type="button" onClick={onResume}>Genoptag</button>{' '}
      <button type="button" onClick={onAbort}>Afbryd</button>
    </div>
  )
}
