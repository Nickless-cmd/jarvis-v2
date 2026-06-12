/** Konverter ASCII-emoticons til rigtige emoji ved afsendelse, så de vises som
 *  smileys i bruger-boblen (og Jarvis modtager den rigtige emoji). Boundary-krav:
 *  emoticon skal følges af mellemrum, slut eller tegnsætning — så URLs (http://)
 *  og kode ikke rammes. (`:/` konverteres bevidst IKKE — for mange false positives.) */
const RULES: [RegExp, string][] = [
  [/;-?\)(?=\s|$|[.,!?])/g, '😉'],
  [/:-?\)(?=\s|$|[.,!?])/g, '🙂'],
  [/:-?\((?=\s|$|[.,!?])/g, '🙁'],
  [/:-?D(?=\s|$|[.,!?])/g, '😄'],
  [/:-?[Pp](?=\s|$|[.,!?])/g, '😛'],
  [/:-?[oO](?=\s|$|[.,!?])/g, '😮'],
  [/:'\((?=\s|$|[.,!?])/g, '😢'],
  [/:\*(?=\s|$|[.,!?])/g, '😘'],
  [/[xX]D(?=\s|$|[.,!?])/g, '😆'],
  [/<3(?=\s|$|[.,!?])/g, '❤️'],
]

export function emojify(text: string): string {
  let out = text
  for (const [re, emoji] of RULES) out = out.replace(re, emoji)
  return out
}
