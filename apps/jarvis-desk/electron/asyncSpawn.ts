import { spawn } from 'node:child_process'
import { StringDecoder } from 'node:string_decoder'

export interface AsyncSpawnDelta {
  stream: 'stdout' | 'stderr'
  seq: number
  chunk: string
}

export interface AsyncSpawnResult {
  stdout: string
  stderr: string
  status: number | null
  signal: string | null
  timed_out: boolean
  error?: string
  dispatch_to_spawn_ms: number
  first_output_ms: number | null
  process_ms: number
  had_output: boolean
}

export async function asyncSpawn(
  cmd: string,
  args: string[],
  opts: { cwd?: string; timeout?: number; maxBuffer?: number } = {},
  onOutput?: (delta: AsyncSpawnDelta) => void,
): Promise<AsyncSpawnResult> {
  return new Promise((resolve) => {
    const startedAt = Date.now()
    const child = spawn(cmd, args, {
      cwd: opts.cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: false,
    })
    const spawnedAt = Date.now()
    const stdoutBuf: Buffer[] = []
    const stderrBuf: Buffer[] = []
    const decoders = {
      stdout: new StringDecoder('utf8'),
      stderr: new StringDecoder('utf8'),
    }
    let firstOutputAt: number | null = null
    let sequence = 0
    let pendingChars = 0
    let pending: Array<{ stream: 'stdout' | 'stderr'; chunk: string }> = []
    let flushTimer: ReturnType<typeof setTimeout> | undefined

    const flushOutput = (): void => {
      if (flushTimer) clearTimeout(flushTimer)
      flushTimer = undefined
      if (!onOutput || pending.length === 0) {
        pending = []
        pendingChars = 0
        return
      }
      const batches: Array<{ stream: 'stdout' | 'stderr'; chunk: string }> = []
      for (const item of pending) {
        const last = batches[batches.length - 1]
        if (last?.stream === item.stream) last.chunk += item.chunk
        else batches.push({ ...item })
      }
      pending = []
      pendingChars = 0
      for (const item of batches) {
        try {
          onOutput({ ...item, seq: ++sequence })
        } catch {
          // Live output is a lossy projection; final collection remains authoritative.
        }
      }
    }

    const queueOutput = (stream: 'stdout' | 'stderr', chunk: string): void => {
      if (!chunk || !onOutput) return
      pending.push({ stream, chunk })
      pendingChars += chunk.length
      if (pendingChars >= 8 * 1024) flushOutput()
      else if (!flushTimer) flushTimer = setTimeout(flushOutput, 75)
    }

    const collect = (stream: 'stdout' | 'stderr', data: Buffer): void => {
      if (firstOutputAt === null) firstOutputAt = Date.now()
      if (stream === 'stdout') stdoutBuf.push(data)
      else stderrBuf.push(data)
      queueOutput(stream, decoders[stream].write(data))
    }
    child.stdout?.on('data', (data: Buffer) => collect('stdout', data))
    child.stderr?.on('data', (data: Buffer) => collect('stderr', data))

    let timedOut = false
    let timer: ReturnType<typeof setTimeout> | undefined
    if (opts.timeout && opts.timeout > 0) {
      timer = setTimeout(() => {
        timedOut = true
        child.kill('SIGTERM')
      }, opts.timeout)
    }

    child.on('close', (code, sig) => {
      if (timer) clearTimeout(timer)
      queueOutput('stdout', decoders.stdout.end())
      queueOutput('stderr', decoders.stderr.end())
      flushOutput()
      const maxBuf = opts.maxBuffer ?? 5 * 1024 * 1024
      let stdout = Buffer.concat(stdoutBuf).toString('utf8')
      let stderr = Buffer.concat(stderrBuf).toString('utf8')
      if (stdout.length > maxBuf) stdout = stdout.slice(0, maxBuf)
      if (stderr.length > maxBuf) stderr = stderr.slice(0, maxBuf)
      const endedAt = Date.now()
      resolve({
        stdout,
        stderr,
        status: code,
        signal: sig,
        timed_out: timedOut,
        dispatch_to_spawn_ms: Math.max(0, spawnedAt - startedAt),
        first_output_ms: firstOutputAt === null ? null : Math.max(0, firstOutputAt - startedAt),
        process_ms: Math.max(0, endedAt - spawnedAt),
        had_output: stdoutBuf.length > 0 || stderrBuf.length > 0,
      })
    })
    child.on('error', (err) => {
      if (timer) clearTimeout(timer)
      flushOutput()
      resolve({
        stdout: '', stderr: '', status: null, signal: null, timed_out: false,
        error: err.message,
        dispatch_to_spawn_ms: Math.max(0, spawnedAt - startedAt),
        first_output_ms: null,
        process_ms: Math.max(0, Date.now() - spawnedAt),
        had_output: false,
      })
    })
  })
}
