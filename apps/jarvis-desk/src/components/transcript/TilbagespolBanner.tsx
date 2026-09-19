/**
 * Banneret efter en tilbagespoling — Claude Desktops tre løfter i én linje:
 * beskederne kan komme tilbage, filerne er uændrede, og fortryd lukker ved
 * næste besked.
 */
export function TilbagespolBanner({ fjernet, fejl, onFortryd, onLuk }: {
  fjernet: number | null
  fejl: string
  onFortryd: () => void
  onLuk: () => void
}) {
  if (fjernet == null && !fejl) return null
  return (
    <div className="tilbagespol-banner" role="status" data-testid="tilbagespol-banner">
      {fjernet != null ? (
        <>
          <span className="tilbagespol-tekst">
            Spolede tilbage — {fjernet} {fjernet === 1 ? 'besked' : 'beskeder'} fjernet. Dine filer er uændrede.
            <span className="tilbagespol-hint"> Fortryd virker indtil du sender en ny besked.</span>
          </span>
          <button type="button" className="tilbagespol-fortryd" onClick={onFortryd}>Fortryd</button>
        </>
      ) : null}
      {fejl ? <span className="tilbagespol-fejl">{fejl}</span> : null}
      <button type="button" className="tilbagespol-luk" aria-label="Luk" onClick={onLuk}>×</button>
    </div>
  )
}
