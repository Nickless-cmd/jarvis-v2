export const tokens = {
  color: {
    bg0: '#0d1117',
    bg1: '#131922',
    bg2: '#1a212d',
    bg3: '#232b39',
    line: '#1f2733',
    fg1: '#e8eaed',
    fg2: '#a8b0bd',
    fg3: '#6b7480',
    accent: '#6ee7a8',
    userBubble: '#1f2837',
    codeBg: '#0a0e14',
    error: '#ff8080',
    warn: '#ffd166',
    // §3 design-sprog: dark = dybde (lag), én accent, glas.
    depth0: '#0D0D12',
    depth1: '#10151d',
    depth2: '#131922',
    depth3: '#1a212d',
    accentDim: 'rgba(110, 231, 168, 0.55)',
    accentGhost: 'rgba(110, 231, 168, 0.12)',
    glassFill: 'rgba(255, 255, 255, 0.07)',
    glassLine: 'rgba(255, 255, 255, 0.10)'
  },
  radius: {
    sm: 6,
    md: 8,
    lg: 12
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24
  },
  // Animations-sandhed (ms). breath = liveness-åndedræt, heartbeat = notif-prik.
  motion: {
    durFast: 160,
    durBase: 250,
    breath: 3000,
    heartbeat: 1400
  }
} as const
