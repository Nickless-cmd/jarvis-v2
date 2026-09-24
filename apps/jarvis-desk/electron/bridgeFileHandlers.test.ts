import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { fileToolHandlers } from './bridgeFileHandlers'

const sha = (text: string) => createHash('sha256').update(text).digest('hex')

describe('operator file undo bridge', () => {
  it('distinguishes a missing file from an empty one', () => {
    const dir = mkdtempSync(join(tmpdir(), 'jarvis-undo-'))
    const path = join(dir, 'new.txt')
    expect(fileToolHandlers.operator_file_snapshot({ path })).toEqual({ exists: false })
    writeFileSync(path, '')
    expect(fileToolHandlers.operator_file_snapshot({ path })).toMatchObject({ exists: true, content: '' })
  })

  it('removes a new file only while its content and mode match', () => {
    const dir = mkdtempSync(join(tmpdir(), 'jarvis-undo-'))
    const path = join(dir, 'new.txt')
    writeFileSync(path, 'created')
    const state = fileToolHandlers.operator_file_snapshot({ path }) as { mode: number }
    expect(() => fileToolHandlers.operator_remove_file({ path, expected_sha256: sha('other'), expected_mode: state.mode }))
      .toThrow(/changed/i)
    expect(readFileSync(path, 'utf8')).toBe('created')
    expect(fileToolHandlers.operator_remove_file({ path, expected_sha256: sha('created'), expected_mode: state.mode }))
      .toEqual({ removed: true, path })
    expect(fileToolHandlers.operator_file_snapshot({ path })).toEqual({ exists: false })
  })
})
