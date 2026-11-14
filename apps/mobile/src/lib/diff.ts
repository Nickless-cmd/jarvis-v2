export type DiffLine = { type: 'same' | 'add' | 'del'; text: string }

/** Minimal linje-diff: fælles prefix/suffix + midten som del-så-add.
 *  Ikke en optimal LCS, men læsbar nok til v1 enkelt-fil-visning. */
export function lineDiff(oldText: string, newText: string): DiffLine[] {
  const a = oldText === '' ? [] : oldText.split('\n')
  const b = newText === '' ? [] : newText.split('\n')
  let lo = 0
  while (lo < a.length && lo < b.length && a[lo] === b[lo]) lo++
  let hiA = a.length, hiB = b.length
  while (hiA > lo && hiB > lo && a[hiA - 1] === b[hiB - 1]) { hiA--; hiB-- }
  const out: DiffLine[] = []
  for (let i = 0; i < lo; i++) out.push({ type: 'same', text: a[i] as string })
  for (let i = lo; i < hiA; i++) out.push({ type: 'del', text: a[i] as string })
  for (let i = lo; i < hiB; i++) out.push({ type: 'add', text: b[i] as string })
  for (let i = hiA; i < a.length; i++) out.push({ type: 'same', text: a[i] as string })
  return out
}
