/**
 * Billede-IPC — rækkevisningen viser et billede fra en lokal sti.
 *
 * ## Hvorfor den findes
 *
 * CSP'en er `img-src 'self' data: blob:`, og renderer'en kan ikke læse disken.
 * Et `<img src="file:///tmp/x.png">` kan derfor ikke vises — uanset hvor rigtig
 * stien er. Main læser filen og giver den tilbage som data-URL: den eneste vej
 * der både virker og holder renderer'en uden disk-adgang.
 *
 * ## Grænsen
 *
 * Kun billed-extensioner. Uden den kunne et fjendtligt tool-resultat få
 * renderer'en til at trække vilkårlige filer ud som base64. Loftet holder et
 * stort billede fra at sprænge IPC-kanalen.
 *
 * Mønsteret er det samme som `figur` og `markoer`: main ejer evnen, renderer
 * spørger, og registreringen sker fra main.ts.
 */
import { ipcMain } from 'electron'
import * as fs from 'node:fs'
import * as path from 'node:path'

const MIME: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.avif': 'image/avif',
}

/** 12 MB. Et fuldt skærmbillede er ~2 MB — resten er ikke noget vi viser. */
const LOFT = 12 * 1024 * 1024

/** Læs en lokal billedfil som data-URL. `null` hvis stien ikke er et billede,
 *  ikke findes, eller er for stor. Gætter aldrig på mime ud fra indholdet —
 *  extensionen bestemmer, så en omdøbt fil ikke får lov at smutte igennem. */
export function laesBillede(sti: string): string | null {
  if (typeof sti !== 'string' || !path.isAbsolute(sti)) return null
  const mime = MIME[path.extname(sti).toLowerCase()]
  if (!mime) return null
  try {
    const stat = fs.statSync(sti)
    if (!stat.isFile() || stat.size > LOFT) return null
    return `data:${mime};base64,${fs.readFileSync(sti).toString('base64')}`
  } catch {
    return null
  }
}

export function registrerBilledeIpc(): void {
  ipcMain.handle('billede:laes', (_e, sti: string) => laesBillede(sti))
}
