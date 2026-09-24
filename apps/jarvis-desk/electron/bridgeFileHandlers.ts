/** File handlers for the operator bridge, including guarded undo primitives. */
import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync, mkdirSync, lstatSync, unlinkSync } from 'node:fs'
import { dirname } from 'node:path'
import { resolveOperatorPath } from './operatorPathPolicy.js'

type FileHandler = (args: Record<string, unknown>) => unknown
const MAX_SNAPSHOT_BYTES = 2_000_000

export const fileToolHandlers = {
  operator_read_file: (args) => {
    const path = resolveOperatorPath(args.path, args._workspace_root)
    return readFileSync(path, 'utf8')
  },

  operator_write_file: (args) => {
    const path = resolveOperatorPath(args.path)
    const content = String(args.content ?? '')
    let bytes_before: number | null = null
    let was_new_file = true
    try {
      const existing = readFileSync(path, 'utf8')
      bytes_before = Buffer.byteLength(existing, 'utf8')
      was_new_file = false
    } catch { /* file didn't exist — fresh creation */ }
    try {
      mkdirSync(dirname(path), { recursive: true })
    } catch { /* writeFileSync below reports a real failure */ }
    writeFileSync(path, content, 'utf8')
    const bytes_after = Buffer.byteLength(content, 'utf8')
    return {
      bytes_written: bytes_after,
      bytes_before,
      bytes_after,
      was_new_file,
      delta_bytes: bytes_before == null ? bytes_after : bytes_after - bytes_before,
      path,
    }
  },

  operator_edit_file: (args) => {
    const path = resolveOperatorPath(args.path)
    const oldStr = String(args.old_string ?? '')
    const newStr = String(args.new_string ?? '')
    const replaceAll = Boolean(args.replace_all)
    if (!oldStr) throw new Error('old_string is required and must be non-empty')
    const orig = readFileSync(path, 'utf8')
    const occurrences = orig.split(oldStr).length - 1
    if (occurrences === 0) {
      throw new Error(`old_string not found in ${path}`)
    }
    if (occurrences > 1 && !replaceAll) {
      throw new Error(
        `old_string appears ${occurrences} times in ${path}; set replace_all=true to replace all, or provide more context`,
      )
    }
    const updated = replaceAll
      ? orig.split(oldStr).join(newStr)
      : orig.replace(oldStr, newStr)
    writeFileSync(path, updated, 'utf8')
    const oldLines = oldStr.split('\n')
    const newLines = newStr.split('\n')
    const maxPreviewLines = 30
    const truncLine = (s: string) => (s.length > 200 ? s.slice(0, 200) + ' …[truncated]' : s)
    const diff_preview = [
      `--- ${path} (before)`,
      `+++ ${path} (after)`,
      ...oldLines.slice(0, maxPreviewLines).map((l) => '-' + truncLine(l)),
      ...(oldLines.length > maxPreviewLines ? [`-… (${oldLines.length - maxPreviewLines} more removed lines)`] : []),
      ...newLines.slice(0, maxPreviewLines).map((l) => '+' + truncLine(l)),
      ...(newLines.length > maxPreviewLines ? [`+… (${newLines.length - maxPreviewLines} more added lines)`] : []),
    ].join('\n')
    return {
      replacements: replaceAll ? occurrences : 1,
      path,
      diff_preview,
      bytes_before: Buffer.byteLength(orig, 'utf8'),
      bytes_after: Buffer.byteLength(updated, 'utf8'),
    }
  },

  /** A missing file is a valid snapshot. Transport errors remain errors. */
  operator_file_snapshot: (args) => {
    const path = resolveOperatorPath(args.path, args._workspace_root)
    let info
    try {
      info = lstatSync(path)
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') return { exists: false }
      throw error
    }
    if (!info.isFile() || info.isSymbolicLink() || info.size > MAX_SNAPSHOT_BYTES) {
      throw new Error('file cannot be safely snapshotted')
    }
    const bytes = readFileSync(path)
    if (bytes.length > MAX_SNAPSHOT_BYTES) throw new Error('file is too large for undo')
    const content = bytes.toString('utf8')
    if (!Buffer.from(content, 'utf8').equals(bytes)) throw new Error('binary file cannot be safely snapshotted')
    return { exists: true, content, mode: info.mode & 0o777 }
  },

  /** The backend uses this only for files created by the selected message. */
  operator_remove_file: (args) => {
    const path = resolveOperatorPath(args.path, args._workspace_root)
    const expectedSha = String(args.expected_sha256 ?? '')
    const expectedMode = Number(args.expected_mode)
    if (!/^[a-f0-9]{64}$/.test(expectedSha) || !Number.isInteger(expectedMode)) {
      throw new Error('expected file fingerprint is required')
    }
    const info = lstatSync(path)
    if (!info.isFile() || info.isSymbolicLink() || info.size > MAX_SNAPSHOT_BYTES) {
      throw new Error('file changed since Jarvis created it')
    }
    const bytes = readFileSync(path)
    if (createHash('sha256').update(bytes).digest('hex') !== expectedSha || (info.mode & 0o777) !== expectedMode) {
      throw new Error('file changed since Jarvis created it')
    }
    unlinkSync(path)
    return { removed: true, path }
  },
} satisfies Record<string, FileHandler>
