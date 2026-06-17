import { execFile } from 'node:child_process'

export const REQUIRED_TOOLS = ['git', 'gh', 'node', 'rg'] as const
export type Tool = typeof REQUIRED_TOOLS[number]
export interface ToolStatus { tool: Tool; present: boolean }

/** Findes værktøjet i PATH? Injicérbar for test. */
export async function defaultWhich(tool: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (process.platform === 'win32') {
      execFile('where', [tool], (err) => resolve(!err))
    } else {
      execFile('/bin/sh', ['-c', `command -v ${tool}`], (err) => resolve(!err))
    }
  })
}

export async function detectTools(
  which: (t: string) => Promise<boolean> = defaultWhich,
): Promise<ToolStatus[]> {
  return Promise.all(REQUIRED_TOOLS.map(async (tool) => ({ tool, present: await which(tool) })))
}
