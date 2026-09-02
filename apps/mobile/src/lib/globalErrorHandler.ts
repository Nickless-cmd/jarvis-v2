/** Global fanger for IKKE-render throws (async-callbacks, timers, event-loop) som
 *  et React-ErrorBoundary aldrig ser. Uden dette lander en ufanget throw i RN's
 *  default-handler (rød skærm i dev, tavs crash i release). Vi logger den og lader
 *  den fortsætte til default'en, så vi ikke skjuler ægte fatale fejl. */
type ErrorUtilsLike = {
  getGlobalHandler?: () => ((error: unknown, isFatal?: boolean) => void) | undefined
  setGlobalHandler?: (handler: (error: unknown, isFatal?: boolean) => void) => void
}

let installed = false

export function installGlobalErrorHandler(): void {
  if (installed) return
  const eu = (globalThis as { ErrorUtils?: ErrorUtilsLike }).ErrorUtils
  if (!eu?.setGlobalHandler) return
  installed = true
  const previous = eu.getGlobalHandler?.()
  eu.setGlobalHandler((error: unknown, isFatal?: boolean) => {
    const err = error as { message?: string; stack?: string } | undefined
    // eslint-disable-next-line no-console
    console.error(
      '[jarvis-mobile global crash]',
      isFatal ? 'FATAL' : 'non-fatal',
      String(err?.message ?? error),
      String(err?.stack ?? '')
    )
    previous?.(error, isFatal)
  })
}
