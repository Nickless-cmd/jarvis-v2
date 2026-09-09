import { mkdirSync, mkdtempSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { resolveOperatorPath } from './operatorPathPolicy'

describe('operator workspace path policy', () => {
  it('allows an existing file inside the selected workspace', () => {
    const root = mkdtempSync(join(tmpdir(), 'jarvis-desk-root-'))
    const file = join(root, 'README.md')
    writeFileSync(file, 'ok')
    expect(resolveOperatorPath(file, root)).toBe(file)
  })
  it('rejects parent traversal outside the selected workspace', () => {
    const root = mkdtempSync(join(tmpdir(), 'jarvis-desk-root-'))
    expect(() => resolveOperatorPath(join(root, '..', 'secret.txt'), root))
      .toThrow(/outside selected workspace/i)
  })
  it('rejects a symlink that resolves outside the selected workspace', () => {
    const root = mkdtempSync(join(tmpdir(), 'jarvis-desk-root-'))
    const outside = mkdtempSync(join(tmpdir(), 'jarvis-desk-outside-'))
    const secret = join(outside, 'secret.txt')
    const linkDir = join(root, 'linked')
    mkdirSync(linkDir)
    writeFileSync(secret, 'secret')
    symlinkSync(secret, join(linkDir, 'secret.txt'))
    expect(() => resolveOperatorPath(join(linkDir, 'secret.txt'), root))
      .toThrow(/outside selected workspace/i)
  })
  it('allows a selected workspace whose root itself is a symlink', () => {
    const parent = mkdtempSync(join(tmpdir(), 'jarvis-desk-parent-'))
    const realRoot = join(parent, 'real-root')
    const linkedRoot = join(parent, 'linked-root')
    mkdirSync(realRoot)
    symlinkSync(realRoot, linkedRoot)
    const file = join(linkedRoot, 'README.md')
    writeFileSync(file, 'ok')
    expect(resolveOperatorPath(file, linkedRoot)).toBe(file)
  })
})
