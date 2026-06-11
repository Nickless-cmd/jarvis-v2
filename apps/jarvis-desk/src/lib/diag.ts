/** Midlertidig in-app diagnostik — vises i et hjørne-panel så vi kan læse
 *  send-flowet via screenshot. Fjernes når ny-samtale-bug er løst. */
const log: string[] = []

export function pushDiag(line: string): void {
  log.push(`${log.length}: ${line}`)
  if (log.length > 40) log.shift()
}

export function getDiag(): string[] {
  return log.slice(-14)
}
