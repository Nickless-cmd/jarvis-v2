/**
 * Kort visningsnavn for en model.
 *
 * Komponisten viste hele strengen — «deepseek · deepseek-v4-flash» — og den
 * åd over halvdelen af knapperækken. ChatGPT viser slet ingen modeltekst i
 * komponisten; vi vil gerne kunne SE hvem der svarer, men ikke betale den
 * fulde bredde for det.
 *
 * Reglen: udbyderen står allerede først i modelnavnet, så den gentagelse ryger.
 * Bliver der intet meningsfuldt tilbage, beholder vi det vi fik — hellere en
 * lang etiket end en tom.
 */
export function shortModelLabel(full: string | undefined | null): string {
  const raw = String(full ?? '').trim()
  if (!raw) return ''

  // «udbyder · model» → behold modellen.
  const parts = raw.split('·').map((p) => p.trim()).filter(Boolean)
  const provider = parts.length > 1 ? parts[0]! : ''
  let model = parts.length > 1 ? parts[parts.length - 1]! : raw

  // «deepseek-v4-flash» med udbyderen «deepseek» → «v4-flash».
  if (provider) {
    const p = provider.toLowerCase()
    const m = model.toLowerCase()
    if (m.startsWith(p + '-') || m.startsWith(p + '/') || m.startsWith(p + ':')) {
      model = model.slice(provider.length + 1)
    } else if (m.startsWith(p) && model.length > provider.length) {
      model = model.slice(provider.length).replace(/^[-/:._]/, '')
    }
  }

  // «openai/gpt-5» → «gpt-5»: en skråstreg er også en udbyder-præfiks.
  const slash = model.lastIndexOf('/')
  if (slash >= 0 && slash < model.length - 1) model = model.slice(slash + 1)

  return model.trim() || raw
}
