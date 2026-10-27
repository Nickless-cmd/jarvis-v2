/**
 * Lille bro mellem en klikket side-opgave-reference i markdown og
 * side-opgave-panelet (som bor i CodeView/ChatView's lokale state).
 *
 * Panelet selv er et `usePersistedState`-boolean — der findes ingen fælles
 * store for "hvilken opgave skal fremhæves lige nu". Denne modul-scope event
 * er den enkleste bro der ikke kræver en ny prop ned gennem MarkdownBlok
 * (som er `memo`'et — se MarkdownRenderer.tsx for hvorfor det er følsomt).
 */

export const SIDE_OPGAVE_AABN_EVENT = 'jarvis:side-opgave-aabn'

export type SideOpgaveAabnDetail = { id: string }

/** Kaldes fra MarkdownRenderer's link-onClick. Åbner panelet (lytter i
 *  CodeView/ChatView) og fremhæver opgaven (lytter i SideOpgaveListe). */
export function aabnSideOpgave(id: string): void {
  window.dispatchEvent(new CustomEvent<SideOpgaveAabnDetail>(SIDE_OPGAVE_AABN_EVENT, { detail: { id } }))
}
