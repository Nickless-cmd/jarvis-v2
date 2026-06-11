/** R1: stream brudt, partial bevaret lokalt. "Genoptag" starter en ny tur. */
export function InterruptedBanner({ onResume }: { onResume: () => void }) {
  return (
    <div className="banner banner-warn">
      Forbindelse afbrudt.{' '}
      <button type="button" onClick={onResume}>Genoptag</button>
    </div>
  )
}
