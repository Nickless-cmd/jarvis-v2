import { existsSync, realpathSync } from 'node:fs'
import { homedir } from 'node:os'
import { isAbsolute, join, relative, resolve } from 'node:path'

function expandOperatorPath(p: unknown): string {
  const raw = String(p ?? '').trim()
  if (!raw) throw new Error('path required')
  if (raw === '~') return homedir()
  if (raw.startsWith('~/')) return join(homedir(), raw.slice(2))
  if (isAbsolute(raw)) return resolve(raw)
  return resolve(homedir(), raw)
}

function isWithin(root: string, candidate: string): boolean {
  const rel = relative(root, candidate)
  return rel === '' || (!rel.startsWith('..') && !isAbsolute(rel))
}

export function resolveOperatorPath(p: unknown, workspaceRoot?: unknown): string {
  const candidate = expandOperatorPath(p)
  const rawRoot = String(workspaceRoot ?? '').trim()
  if (!rawRoot) return candidate

  const root = expandOperatorPath(rawRoot)
  if (!isWithin(root, candidate)) throw new Error('Path is outside selected workspace')
  const canonicalRoot = existsSync(root) ? realpathSync(root) : root
  const canonicalCandidate = existsSync(candidate) ? realpathSync(candidate) : candidate
  if (!isWithin(canonicalRoot, canonicalCandidate)) {
    throw new Error('Path is outside selected workspace')
  }
  return candidate
}
