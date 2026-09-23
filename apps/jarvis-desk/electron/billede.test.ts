import { describe, it, expect, vi } from 'vitest'
import * as fs from 'node:fs'
import * as os from 'node:os'
import * as path from 'node:path'

// billede.ts importerer ipcMain fra electron — findes ikke i vitest.
vi.mock('electron', () => ({ ipcMain: { handle: vi.fn() } }))

import { laesBillede } from './billede'

describe('laesBillede — grænsen for hvad main vil læse', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'billede-test-'))

  it('læser en png som data-URL', () => {
    const p = path.join(dir, 'x.png')
    fs.writeFileSync(p, Buffer.from([0x89, 0x50, 0x4e, 0x47]))
    expect(laesBillede(p)).toBe('data:image/png;base64,iVBORw==')
  })

  it('kender jpeg, webp og gif', () => {
    for (const [ext, mime] of [['.jpg', 'image/jpeg'], ['.jpeg', 'image/jpeg'], ['.webp', 'image/webp'], ['.gif', 'image/gif']]) {
      const p = path.join(dir, `x${ext}`)
      fs.writeFileSync(p, Buffer.from([1, 2, 3]))
      expect(laesBillede(p)).toMatch(new RegExp(`^data:${mime};base64,`))
    }
  })

  it('afviser alt der ikke er et billede — også en fil der findes', () => {
    // Uden denne grænse kunne et fjendtligt tool-resultat trække vilkårlige
    // filer ud af disken som base64.
    const txt = path.join(dir, 'hemmelig.txt')
    fs.writeFileSync(txt, 'kodeord')
    expect(laesBillede(txt)).toBeNull()
    expect(laesBillede('/home/bs/.ssh/id_rsa')).toBeNull()
    expect(laesBillede('/etc/passwd')).toBeNull()
  })

  it('afviser relative stier', () => {
    expect(laesBillede('x.png')).toBeNull()
    expect(laesBillede('./x.png')).toBeNull()
  })

  it('returnerer null for en fil der ikke findes', () => {
    expect(laesBillede(path.join(dir, 'findes-ikke.png'))).toBeNull()
  })

  it('afviser en mappe der hedder .png', () => {
    const mappe = path.join(dir, 'mappe.png')
    fs.mkdirSync(mappe)
    expect(laesBillede(mappe)).toBeNull()
  })
})
