/**
 * Plads til de svævende bjælker.
 *
 * Header og komponist ligger `position: absolute` oven på indholdet, så tråden
 * kan rulle bag dem. Alt ANDET ligger i den almindelige kolonne og skal derfor
 * selv holde afstand — ellers står det bag en bjælke, hvor man kan se det men
 * ikke trykke på det.
 *
 * Fælden er den tomme afstandsklods. Første udgave gav indpakningen omkring
 * godkendelses- og fejlkortene bundmargen UBETINGET. Uden et kort blev det til
 * et hul mellem tråden og komponisten — og med tastaturet fremme voksede hullet
 * med tastaturets højde og skubbede hele tråden ud af skærmen.
 *
 * En afstandsklods skal kun findes, når der er noget at holde afstand fra.
 */
export function cardSpacerStyle(
  hasCard: boolean,
  composerHeight: number,
  keyboardLift: number
): { marginBottom: number } | null {
  if (!hasCard) return null
  return { marginBottom: Math.max(0, composerHeight) + Math.max(0, keyboardLift) }
}
