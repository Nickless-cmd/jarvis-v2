export type PkgManager = 'apt' | 'dnf' | 'pacman'
export interface OsCtx { platform: NodeJS.Platform; pkgManager?: PkgManager }
export interface InstallCmd { cmd: string; args: string[] }

// Værktøj → pakkenavn pr. økosystem (rg → ripgrep; node → nodejs på Linux).
const PKG: Record<string, { apt: string; dnf: string; pacman: string; brew: string; winget: string }> = {
  git: { apt: 'git', dnf: 'git', pacman: 'git', brew: 'git', winget: 'Git.Git' },
  gh: { apt: 'gh', dnf: 'gh', pacman: 'github-cli', brew: 'gh', winget: 'GitHub.cli' },
  node: { apt: 'nodejs', dnf: 'nodejs', pacman: 'nodejs', brew: 'node', winget: 'OpenJS.NodeJS' },
  ripgrep: { apt: 'ripgrep', dnf: 'ripgrep', pacman: 'ripgrep', brew: 'ripgrep', winget: 'BurntSushi.ripgrep.MSVC' },
}

export function installCommand(tool: string, ctx: OsCtx): InstallCmd | null {
  const key = tool === 'rg' ? 'ripgrep' : tool
  const p = PKG[key]
  if (!p) return null
  if (ctx.platform === 'darwin') return { cmd: 'brew', args: ['install', p.brew] }
  if (ctx.platform === 'win32') {
    return { cmd: 'winget', args: ['install', '-e', '--id', p.winget, '--accept-source-agreements', '--accept-package-agreements'] }
  }
  const pm = ctx.pkgManager ?? 'apt'
  if (pm === 'apt') return { cmd: 'pkexec', args: ['apt-get', 'install', '-y', p.apt] }
  if (pm === 'dnf') return { cmd: 'pkexec', args: ['dnf', 'install', '-y', p.dnf] }
  return { cmd: 'pkexec', args: ['pacman', '-S', '--noconfirm', p.pacman] }
}
