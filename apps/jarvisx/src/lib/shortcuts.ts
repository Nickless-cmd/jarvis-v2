/**
 * Centralized keyboard-shortcut registry for JarvisX.
 *
 * One source of truth for:
 *   - what shortcuts exist
 *   - how they're rendered in the overlay
 *   - which scope owns them (global vs chat vs composer)
 *
 * Handlers are wired up where they belong (App.tsx for global, ChatView
 * for chat-scoped). The list here is purely descriptive — it's what the
 * shortcut overlay reads to render the cheat sheet.
 *
 * Why central if handlers are decentralized? Because the *list* is the
 * UX promise to the user: "here's what works." Drift between code and
 * docs is the #1 reason shortcuts feel half-broken in apps. Keep them
 * coupled.
 */
export interface Shortcut {
  keys: string[]  // displayable form, e.g. ["Ctrl", "K"]
  label: string
  scope: 'global' | 'chat' | 'composer'
}

export const SHORTCUTS: Shortcut[] = [
  // Global navigation
  { keys: ['Ctrl', '1'], label: 'Hop til Chat', scope: 'global' },
  { keys: ['Ctrl', '2'], label: 'Hop til Mind', scope: 'global' },
  { keys: ['Ctrl', '3'], label: 'Hop til Hukommelse', scope: 'global' },
  { keys: ['Ctrl', '4'], label: 'Hop til Værktøjer', scope: 'global' },
  { keys: ['Ctrl', '5'], label: 'Hop til Claude jobs', scope: 'global' },
  { keys: ['Ctrl', '6'], label: 'Hop til Dashboard', scope: 'global' },
  { keys: ['Ctrl', '7'], label: 'Hop til Channels', scope: 'global' },
  { keys: ['Ctrl', '8'], label: 'Hop til Planlægning', scope: 'global' },
  { keys: ['Ctrl', ','], label: 'Indstillinger', scope: 'global' },

  // Global commands
  { keys: ['Ctrl', 'K'], label: 'Søg på tværs af sessions', scope: 'global' },
  { keys: ['Ctrl', '/'], label: 'Slash-palette', scope: 'global' },
  { keys: ['Ctrl', 'J'], label: 'Toggle terminal-drawer', scope: 'global' },
  { keys: ['Ctrl', 'B'], label: 'Skjul/vis sidebar', scope: 'global' },
  { keys: ['F1'], label: 'Vis denne genvejsoversigt', scope: 'global' },
  { keys: ['Esc'], label: 'Luk åbne dialoger / overlays', scope: 'global' },

  // Chat-scoped
  { keys: ['Ctrl', 'N'], label: 'Ny chat-session', scope: 'chat' },
  { keys: ['Ctrl', 'L'], label: 'Fokuser composer', scope: 'chat' },

  // Composer-scoped (apps/ui Composer owner — listed for discoverability)
  { keys: ['Enter'], label: 'Send besked', scope: 'composer' },
  { keys: ['Shift', 'Enter'], label: 'Ny linje', scope: 'composer' },
  { keys: ['@'], label: 'File-mention autocomplete', scope: 'composer' },
]

/**
 * Match a KeyboardEvent against a "Ctrl+X"-style key spec, ignoring
 * modifier-key state for the modifier itself. Both Ctrl and Meta count
 * as "Ctrl" (Cmd on macOS) so the same shortcuts work on every OS.
 *
 * `digit` matches Digit1..9 / Numpad1..9 (e.code) so it works even on
 * keyboard layouts where the visible label on a digit key is different
 * (rare on numbers, but principle of layout-independence).
 */
export function matchShortcut(
  e: KeyboardEvent,
  spec: { ctrl?: boolean; shift?: boolean; alt?: boolean; key?: string; code?: string; digit?: number },
): boolean {
  if (spec.ctrl !== undefined) {
    const has = e.ctrlKey || e.metaKey
    if (spec.ctrl !== has) return false
  }
  if (spec.shift !== undefined && spec.shift !== e.shiftKey) return false
  if (spec.alt !== undefined && spec.alt !== e.altKey) return false
  if (spec.digit !== undefined) {
    return e.code === `Digit${spec.digit}` || e.code === `Numpad${spec.digit}`
  }
  if (spec.key !== undefined && e.key.toLowerCase() !== spec.key.toLowerCase()) return false
  if (spec.code !== undefined && e.code !== spec.code) return false
  return true
}

/**
 * Should this keyboard event be ignored because the user is typing into
 * a text input / textarea / contenteditable? Without this, every Ctrl+N
 * keystroke inside the composer would clobber the chat session.
 *
 * Exception: shortcuts that are *meant* to fire from inside the composer
 * (Ctrl+L to focus the composer when it's already focused is a no-op,
 * Ctrl+J to toggle terminal should work even from composer) — those
 * pass `allowInInput: true` at their callsite and skip this check.
 */
export function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return true
  if (target.isContentEditable) return true
  return false
}
