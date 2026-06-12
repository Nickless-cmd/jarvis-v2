/** Levende status-verbum: en lysbølge løber gennem ordet (shimmer) + tre prikker
 *  der pulserer som lys der bevæger sig. Bruges i liveness-linjen og i det live
 *  "tænker…"-felt så det føles i live frem for statisk. */
export function LiveVerb({ text }: { text: string }) {
  return (
    <span className="live-verb">
      <span className="shimmer">{text}</span>
      <span className="live-dots" aria-hidden="true"><span /><span /><span /></span>
    </span>
  )
}
