/** Post-connect-hook: når en connector lige er blevet forbundet, gemmer vi et
 *  connector-specifikt hint (fra katalogets post_connect_hint). Næste gang chat-
 *  tom-skærmen vises, tilbyder GreetingHero hintet ("Nu kan jeg kigge i dine
 *  GitHub-issues — skal jeg?"). Engangs-forbrug. */
const KEY = 'jarvis-desk:post-connect-hint'

export function setPendingHint(hint: string | null | undefined): void {
  try {
    if (hint && hint.trim()) localStorage.setItem(KEY, hint.trim())
  } catch { /* private mode / ingen storage — drop stille */ }
}

/** Hent + ryd hintet (engangs). Null hvis intet. */
export function takePendingHint(): string | null {
  try {
    const v = localStorage.getItem(KEY)
    if (v) localStorage.removeItem(KEY)
    return v || null
  } catch {
    return null
  }
}
