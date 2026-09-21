import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { HANDLENDE_TOOLS, erHandlende } from './markoerTools'

describe('erHandlende', () => {
  it('kender de handlende vaerktoejer', () => {
    expect(erHandlende('operator_mouse_click')).toBe(true)
    expect(erHandlende('operator_keyboard_type')).toBe(true)
  })

  it('laesning er IKKE en overtagelse', () => {
    // At tage et skaermbillede eller laese markoerens position er at KIGGE.
    // Tændte det halo'en, ville den lyse naar Jarvis blot orienterer sig.
    for (const t of [
      'operator_screenshot',
      'operator_screenshot_window',
      'operator_screen_size',
      'operator_mouse_position',
      'operator_list_windows',
      'operator_ocr_region',
      'operator_find_image',
      'operator_clipboard_read',
    ]) {
      expect(erHandlende(t)).toBe(false)
    }
  })

  it('ukendte navne taeller ikke', () => {
    expect(erHandlende('bash')).toBe(false)
    expect(erHandlende('')).toBe(false)
    expect(erHandlende('operator_')).toBe(false)
  })

  it('listen er unik og uden tomme navne', () => {
    expect(new Set(HANDLENDE_TOOLS).size).toBe(HANDLENDE_TOOLS.length)
    expect(HANDLENDE_TOOLS.every((t) => t.length > 0)).toBe(true)
    expect(HANDLENDE_TOOLS.every((t) => t.startsWith('operator_'))).toBe(true)
  })

  // Denne test er pointen med filen: to lister over samme familie driver fra
  // hinanden foer eller siden. Her laeses Python-siden, og testen fejler i det
  // oejeblik de ikke laengere er enige — saa halo'en og samtykke-porten altid
  // taender for praecis de samme handlinger.
  it('matcher samtykke-portens HANDLENDE i Python', () => {
    const py = readFileSync(
      join(process.cwd(), '../../core/services/computer_use_samtykke.py'),
      'utf8',
    )
    const start = py.indexOf('HANDLENDE')
    const slut = py.indexOf('LAESENDE')
    expect(start).toBeGreaterThan(-1)
    expect(slut).toBeGreaterThan(start)
    const navne = [...py.slice(start, slut).matchAll(/"(operator_[a-z_]+)"/g)]
      .map((m) => m[1] as string)
      .sort()
    expect(navne.length).toBe(HANDLENDE_TOOLS.length)
    expect([...HANDLENDE_TOOLS].sort()).toEqual(navne)
  })
})
