import { getSingletonHighlighter, type BundledLanguage, type Highlighter } from 'shiki'

const THEMES = { light: 'github-light', dark: 'github-dark' } as const
type TokenResult = ReturnType<Highlighter['codeToTokens']>

export interface ChatHighlight {
  code: string
  lang: string
  tokens: TokenResult['tokens']
  grammarState: TokenResult['grammarState']
}

/** 29/9-2026: den åbne fence får kun afsluttede linjer. Når en ny linje
 *  tilføjes, fortsætter Shiki fra den tidligere grammatiktilstand i stedet
 *  for at tokenisere hele den voksende kodeblok igen. */
/**
 * KENDT BEGRAENSNING — accepteret, ikke en fejl (spec punkt 9, 30/9-2026).
 *
 * En lang highlightet fence beholder HELE sit token-DOM. Streaming undgaar
 * re-parse og re-tokenize ved at foere grammatik-tilstanden videre og kun
 * tokenisere det nye, men den smider ikke gamle farver vaek og virtualiserer
 * ikke spans. Den endelige DOM-stoerrelse foelger derfor token-antallet.
 *
 * DSH skriver den samme begraensning hoejt om sin egen implementering. Den
 * staar her for at den ikke bliver «opfoert» som en fejl senere.
 */
export function tokenizeChatCode(
  highlighter: Highlighter,
  code: string,
  lang: string,
  previous: ChatHighlight | null,
): ChatHighlight {
  if (previous?.code === code && previous.lang === lang) return previous
  const append = previous?.lang === lang && previous.code.endsWith('\n')
    && code.startsWith(previous.code) && !!previous.grammarState
  const input = append ? code.slice(previous.code.length) : code
  const result = highlighter.codeToTokens(input, {
    lang: lang as BundledLanguage,
    themes: THEMES,
    defaultColor: false,
    ...(append ? { grammarState: previous.grammarState } : {}),
  })
  return {
    code,
    lang,
    tokens: append ? [...previous.tokens.slice(0, -1), ...result.tokens] : result.tokens,
    grammarState: result.grammarState,
  }
}

export async function highlightChatCode(
  code: string,
  lang: string,
  previous: ChatHighlight | null,
): Promise<ChatHighlight> {
  const highlighter = await getSingletonHighlighter({
    themes: ['github-light', 'github-dark'],
    langs: [lang as BundledLanguage],
  })
  return tokenizeChatCode(highlighter, code, lang, previous)
}
