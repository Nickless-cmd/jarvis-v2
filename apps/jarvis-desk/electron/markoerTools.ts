/**
 * Hvilke værktøjer der tæller som «Jarvis overtager skærmen».
 *
 * Bjørn 21/9-2026: «en halo hele vejen rundt skærmen — et eller andet der
 * indikerer du overtager skærmen». Halo'en tændes af de HANDLENDE værktøjer og
 * ikke af de læsende: at tage et skærmbillede er at kigge, ikke at overtage.
 * Det er samme skelnen samtykke-porten bruger — kun de handlende kræver et ja.
 *
 * Listen er bevidst den SAMME familie som `core/services/computer_use_samtykke.py`
 * → `HANDLENDE`. To lister over samme familie driver fra hinanden før eller
 * siden; `markoerTools.test.ts` læser Python-filen og fejler, hvis de gør.
 *
 * Ren fil uden electron-import, så den kan testes uden en skærm.
 */

export const HANDLENDE_TOOLS: readonly string[] = [
  'operator_mouse_click',
  'operator_mouse_move',
  'operator_mouse_drag',
  'operator_mouse_scroll',
  'operator_keyboard_type',
  'operator_keyboard_press',
  'operator_clipboard_write',
  'operator_focus_window',
  'operator_launch_app',
]

/** Rører dette værktøj skærmen — eller kigger det blot? */
export function erHandlende(tool: string): boolean {
  return HANDLENDE_TOOLS.includes(tool)
}
