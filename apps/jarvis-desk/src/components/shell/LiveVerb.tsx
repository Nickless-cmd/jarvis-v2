/** Levende status-verbum: en lysbølge løber gennem ordet (shimmer) + husets
 *  eget mærke — tre streger der ånder. Bruges i liveness-linjen og i det live
 *  "tænker…"-felt så det føles i live frem for statisk.
 *
 *  9/11-2026: stregerne erstattede tre prikker. Bjørn pegede på Claude Codes
 *  fire bolde som det der føles levende, og på vores som det der bare blinker.
 *  Årsagen lå ikke i antallet, men i to ting — at vores prikker gik til opacity
 *  0 i hver cyklus, og at bevægelsen kun var lysstyrke. Se `.live-streger` i
 *  app.css. Tre streger, ikke fire bolde: antallet er husets, bevægelsen er
 *  den vi lærte af deres. */
export function LiveVerb({ text }: { text: string }) {
  return (
    <span className="live-verb">
      <span className="shimmer">{text}</span>
      <span className="live-streger" aria-hidden="true"><span /><span /><span /></span>
    </span>
  )
}
