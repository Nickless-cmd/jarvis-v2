import { useEffect, useRef } from 'react'

/**
 * Spec E / E1 — orb-tieren. Renderer Jarvis' tilstedeværelse client-side (WebGL2D canvas),
 * drevet af Centralens ÆGTE valens (fra /presence/state). Fire stilarter. Ingen server-pixels.
 * `speaking` (fra TTS-afspilning, E2) giver puls-boost + hurtigere bevægelse.
 */
export type OrbStyle = 'reactor' | 'hud' | 'core' | 'wave'
export type Valence = { tone: string; score: number; intensity: number; trend?: string | null }

const PAL: Record<string, { c: string; c2: string; energy: number; calm: number }> = {
  blomstrende: { c: '#ffd36b', c2: '#ff9d3c', energy: 1.0, calm: 0 },
  let: { c: '#5fe3ab', c2: '#1d9e75', energy: 0.7, calm: 0.3 },
  neutral: { c: '#9cc4ff', c2: '#378add', energy: 0.45, calm: 0.5 },
  tung: { c: '#6b8fd6', c2: '#2b4f8f', energy: 0.28, calm: 0.8 },
  belastet: { c: '#ff7a6b', c2: '#c0392b', energy: 0.55, calm: 0.1 },
}

export function PresenceOrb({ style, valence, speaking = false, height = 220 }: {
  style: OrbStyle; valence: Valence; speaking?: boolean; height?: number
}) {
  const ref = useRef<HTMLCanvasElement | null>(null)
  const vref = useRef({ valence, style, speaking })
  vref.current = { valence, style, speaking }

  useEffect(() => {
    const cvs = ref.current
    if (!cvs) return
    const ctx = cvs.getContext('2d')
    if (!ctx) return
    let raf = 0
    let dims = { w: 0, h: 0 }
    const fit = () => {
      const r = cvs.getBoundingClientRect(); const d = window.devicePixelRatio || 1
      cvs.width = Math.max(1, r.width * d); cvs.height = Math.max(1, r.height * d)
      ctx.setTransform(d, 0, 0, d, 0, 0); dims = { w: r.width, h: r.height }
    }
    fit(); window.addEventListener('resize', fit)

    const speak = (t: number, boost: boolean) =>
      (boost ? 0.45 : 0.15) + 0.55 * Math.sin(t * 4) * Math.max(0, Math.sin(t * 0.7))

    const draw = (nowMs: number) => {
      const t = nowMs / 1000
      const { valence: v, style: s, speaking: sp } = vref.current
      const p = PAL[v?.tone ?? 'neutral'] ?? { c: '#9cc4ff', c2: '#378add', energy: 0.45, calm: 0.5 }
      const energy = p.energy * (0.5 + 0.5 * Math.min(1, v?.intensity ?? 0.3) + (sp ? 0.4 : 0))
      const { w, h } = dims
      ctx.clearRect(0, 0, w, h)
      const cx = w / 2, cy = h / 2, R = Math.min(w, h) * 0.34
      const sPulse = speak(t, sp) * energy
      ctx.save(); ctx.translate(cx, cy)

      if (s === 'reactor') {
        for (let i = 0; i < 3; i++) {
          ctx.save(); ctx.rotate(t * (0.3 + i * 0.25) * (i % 2 ? -1 : 1))
          const rr = R * (0.55 + i * 0.22); ctx.strokeStyle = p.c; ctx.globalAlpha = 0.25 + 0.2 * i; ctx.lineWidth = 2
          ctx.beginPath()
          for (let a = 0; a < 12; a++) { const an = a / 12 * Math.PI * 2; const on = a % 3 === 0; ctx.moveTo(Math.cos(an) * rr, Math.sin(an) * rr); ctx.lineTo(Math.cos(an) * rr * (on ? 1.12 : 1.05), Math.sin(an) * rr * (on ? 1.12 : 1.05)) }
          ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, rr, 0, Math.PI * 2); ctx.globalAlpha = 0.12 + 0.08 * i; ctx.stroke(); ctx.restore()
        }
        const cr = R * 0.42 * (1 + 0.12 * sPulse); const g = ctx.createRadialGradient(0, 0, 0, 0, 0, cr * 2.4)
        g.addColorStop(0, p.c); g.addColorStop(0.4, p.c2); g.addColorStop(1, 'transparent')
        ctx.globalAlpha = 0.55 + 0.35 * sPulse; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, cr * 2.4, 0, Math.PI * 2); ctx.fill()
        ctx.globalAlpha = 1; ctx.fillStyle = '#eaf4ff'; ctx.save(); ctx.rotate(-t * 0.6)
        ctx.beginPath(); for (let a = 0; a < 3; a++) { const an = a / 3 * Math.PI * 2 - Math.PI / 2; a ? ctx.lineTo(Math.cos(an) * cr, Math.sin(an) * cr) : ctx.moveTo(Math.cos(an) * cr, Math.sin(an) * cr) } ctx.closePath(); ctx.fill(); ctx.restore()
      } else if (s === 'hud') {
        const RR = Math.min(w, h) * 0.4; ctx.strokeStyle = p.c
        for (let i = 0; i < 4; i++) { ctx.save(); ctx.rotate(t * (0.15 + i * 0.1) * (i % 2 ? -1 : 1)); const rr = RR * (0.35 + i * 0.2); const arc = [0.7, 1.4, 0.5, 2.1][i] ?? 1; ctx.globalAlpha = 0.3 + 0.12 * i; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(0, 0, rr, i * 0.5, i * 0.5 + arc); ctx.stroke(); ctx.beginPath(); ctx.arc(0, 0, rr, i * 0.5 + arc + 0.4, i * 0.5 + arc + 0.4 + arc * 0.6); ctx.stroke(); ctx.restore() }
        ctx.save(); ctx.rotate(-t * 0.4); ctx.globalAlpha = 0.5
        for (let a = 0; a < 40; a++) { const an = a / 40 * Math.PI * 2, r1 = RR * 0.95, r2 = RR * (a % 5 === 0 ? 1.06 : 1.01); ctx.beginPath(); ctx.moveTo(Math.cos(an) * r1, Math.sin(an) * r1); ctx.lineTo(Math.cos(an) * r2, Math.sin(an) * r2); ctx.stroke() } ctx.restore()
        const cr = RR * 0.16 * (1 + 0.25 * sPulse); const g = ctx.createRadialGradient(0, 0, 0, 0, 0, cr * 3); g.addColorStop(0, p.c); g.addColorStop(1, 'transparent')
        ctx.globalAlpha = 0.6 + 0.3 * sPulse; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, cr * 3, 0, Math.PI * 2); ctx.fill()
        ctx.globalAlpha = 0.9; ctx.strokeStyle = '#eaf4ff'; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(0, 0, cr, 0, Math.PI * 2); ctx.stroke()
      } else if (s === 'core') {
        for (let l = 6; l >= 0; l--) { const rr = R * (0.5 + l * 0.12) * (1 + 0.05 * sPulse * Math.sin(t * 2 + l)); const g = ctx.createRadialGradient(Math.sin(t + l) * R * 0.1, Math.cos(t * 0.7 + l) * R * 0.1, 0, 0, 0, rr); g.addColorStop(0, l < 2 ? '#fff' : p.c); g.addColorStop(0.5, p.c2); g.addColorStop(1, 'transparent'); ctx.globalAlpha = 0.14 + 0.03 * l; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(0, 0, rr, 0, Math.PI * 2); ctx.fill() }
        for (let i = 0; i < 26; i++) { const a = i / 26 * Math.PI * 2 + t * (0.4 + p.calm * 0.3), rr = R * (1.05 + 0.5 * ((i * 97) % 10) / 10); ctx.globalAlpha = 0.5 - p.calm * 0.3; ctx.fillStyle = p.c; ctx.beginPath(); ctx.arc(Math.cos(a) * rr, Math.sin(a) * rr, 1.4, 0, Math.PI * 2); ctx.fill() }
        ctx.globalAlpha = 0.9; ctx.strokeStyle = p.c; ctx.lineWidth = 1; ctx.beginPath(); ctx.arc(0, 0, R, 0, Math.PI * 2); ctx.stroke()
      } else {
        ctx.restore(); ctx.save(); ctx.strokeStyle = p.c; ctx.lineWidth = 2
        for (let layer = 0; layer < 3; layer++) { ctx.beginPath(); ctx.globalAlpha = 0.7 - layer * 0.2; for (let px = 0; px <= w; px += 4) { const n = Math.sin(px * 0.02 + t * 3 + layer) + Math.sin(px * 0.05 - t * 2 + layer * 2) * 0.5; const amp = (h * 0.22) * energy * (0.4 + 0.6 * speak(t, sp)) * Math.exp(-Math.pow((px - w / 2) / (w * 0.4), 2)); const y = cy + n * amp * (layer ? 0.5 : 1); px ? ctx.lineTo(px, y) : ctx.moveTo(px, y) } ctx.stroke() }
        const g = ctx.createRadialGradient(w / 2, cy, 0, w / 2, cy, h * 0.3); g.addColorStop(0, p.c); g.addColorStop(1, 'transparent'); ctx.globalAlpha = 0.25 + 0.2 * speak(t, sp) * energy; ctx.fillStyle = g; ctx.fillRect(0, 0, w, h)
      }
      ctx.restore()
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', fit) }
  }, [])

  return (
    <canvas ref={ref} aria-label="Jarvis tilstedeværelse" role="img"
      style={{ width: '100%', height, display: 'block', borderRadius: 14, background: '#04070d' }} />
  )
}
