import { getSingletonHighlighter, type BundledLanguage, type Highlighter } from 'shiki'
import { fallbackTokens } from './kodeFallback'

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

/** Sprognavne der optræder i praksis men ikke findes som grammatik i bundlen.
 *  MÅLT 24/10-2026 over 3.481 kodeblokke: `cron` 95, `jarvis-ui` 34, `|` 17,
 *  `conf`, `shell`, `git`. Uden denne tabel kastede shiki og blokken blev rå
 *  tekst — med den rammer de en grammatik der ligner. */
const ALIAS: Record<string, string> = {
  sh: 'shellscript',
  shell: 'shellscript',
  bash: 'shellscript',
  zsh: 'shellscript',
  cron: 'shellscript',
  crontab: 'shellscript',
  git: 'shellscript',
  console: 'shellscript',
  conf: 'ini',
  cfg: 'ini',
  js: 'javascript',
  ts: 'typescript',
  py: 'python',
  plaintext: 'text',
  plain: 'text',
}

/** Sprog hvor shiki ikke kan give farve: tomt (41 % af alle blokke), `text`
 *  (gyldigt men ensfarvet) og de navne der kun findes som alias til `text`.
 *  De går gennem scanneren i kodeFallback.ts, så en blok uden sprog-tag også
 *  bliver farvet — præcis som mobilen altid har gjort. */
const UDEN_GRAMMATIK = new Set(['', 'text', 'txt', 'plain', 'plaintext', 'output'])

export async function highlightChatCode(
  code: string,
  lang: string,
  previous: ChatHighlight | null,
): Promise<ChatHighlight> {
  const raw = String(lang ?? '').trim().toLowerCase()
  const effective = ALIAS[raw] ?? raw

  if (UDEN_GRAMMATIK.has(raw) || UDEN_GRAMMATIK.has(effective)) {
    return {
      code,
      lang: raw,
      tokens: fallbackTokens(code) as unknown as TokenResult['tokens'],
      grammarState: undefined,
    }
  }

  try {
    const highlighter = await getSingletonHighlighter({
      themes: ['github-light', 'github-dark'],
      langs: [effective as BundledLanguage],
    })
    // `tokenizeChatCode` får det oversatte sprog, men resultatet bærer det
    // ORIGINALE navn: ChatCodeBlock sammenligner `highlighted.lang` med den
    // `lang` den fik i props, og et mismatch ville sende os tilbage til rå tekst.
    const result = tokenizeChatCode(highlighter, code, effective, previous)
    return { ...result, lang: raw }
  } catch {
    return {
      code,
      lang: raw,
      tokens: fallbackTokens(code) as unknown as TokenResult['tokens'],
      grammarState: undefined,
    }
  }
}
