import { useEffect, useRef, useState } from 'react'
import { Volume2, VolumeX } from 'lucide-react'

const PREFS_KEY = 'jarvis_ambient_prefs'
const POLL_INTERVAL_MS = 30_000

const ENERGY_MAP = {
  høj:      { freq: 80, gain: 0.04, filterType: 'peaking',  filterFreq: 200, filterGain: 2 },
  medium:   { freq: 55, gain: 0.03, filterType: 'peaking',  filterFreq: 200, filterGain: 0 },
  lav:      { freq: 40, gain: 0.02, filterType: 'lowshelf', filterFreq: 200, filterGain: -2 },
  udmattet: { freq: 30, gain: 0.01, filterType: 'lowpass',  filterFreq: 80,  filterGain: 0 },
  default:  { freq: 50, gain: 0.02, filterType: 'peaking',  filterFreq: 200, filterGain: 0 },
}

function loadPrefs() {
  try {
    const stored = localStorage.getItem(PREFS_KEY)
    if (stored) return JSON.parse(stored)
  } catch (_) {}
  return { muted: false, volume: 0.3 }
}

function savePrefs(prefs) {
  try { localStorage.setItem(PREFS_KEY, JSON.stringify(prefs)) } catch (_) {}
}

export function AmbientPresence() {
  const prefs = loadPrefs()
  const [muted, setMuted] = useState(prefs.muted)
  const [volume, setVolume] = useState(prefs.volume)

  const audioCtxRef = useRef(null)
  const oscRef = useRef(null)
  const filterRef = useRef(null)
  const gainRef = useRef(null)
  const surpriseTimerRef = useRef(null)
  const abortRef = useRef(null)
  const currentEnergyRef = useRef('default')

  // ── Audio lifecycle ──────────────────────────────────────────────
  function ensureAudioContext() {
    if (audioCtxRef.current) return
    const ctx = new (window.AudioContext || window.webkitAudioContext)()
    const osc = ctx.createOscillator()
    const filter = ctx.createBiquadFilter()
    const gain = ctx.createGain()

    osc.type = 'sine'
    osc.frequency.value = ENERGY_MAP.default.freq
    filter.type = ENERGY_MAP.default.filterType
    filter.frequency.value = ENERGY_MAP.default.filterFreq
    gain.gain.value = prefs.muted ? 0 : prefs.volume * ENERGY_MAP.default.gain

    osc.connect(filter)
    filter.connect(gain)
    gain.connect(ctx.destination)
    osc.start()

    audioCtxRef.current = ctx
    oscRef.current = osc
    filterRef.current = filter
    gainRef.current = gain
  }

  function applyEnergyState(energyLevel, vol, isMuted) {
    const ctx = audioCtxRef.current
    const osc = oscRef.current
    const filter = filterRef.current
    const gain = gainRef.current
    if (!ctx || !osc || !filter || !gain) return

    const params = ENERGY_MAP[energyLevel] || ENERGY_MAP.default
    const now = ctx.currentTime
    const tc = 2.0

    osc.frequency.setTargetAtTime(params.freq, now, tc)
    filter.type = params.filterType
    filter.frequency.setTargetAtTime(params.filterFreq, now, tc)
    if (params.filterType === 'peaking' || params.filterType === 'lowshelf') {
      filter.gain.setTargetAtTime(params.filterGain, now, tc)
    }
    if (!isMuted && !surpriseTimerRef.current) {
      gain.gain.setTargetAtTime(vol * params.gain, now, tc)
    }
  }

  function triggerSurpriseSilence(vol, isMuted) {
    const ctx = audioCtxRef.current
    const gain = gainRef.current
    if (!ctx || !gain) return
    if (surpriseTimerRef.current) return

    const now = ctx.currentTime
    gain.gain.setTargetAtTime(0, now, 0.3)

    surpriseTimerRef.current = setTimeout(() => {
      surpriseTimerRef.current = null
      if (!gainRef.current || !audioCtxRef.current) return
      if (isMuted) return
      const energy = currentEnergyRef.current
      const params = ENERGY_MAP[energy] || ENERGY_MAP.default
      gainRef.current.gain.setTargetAtTime(vol * params.gain, audioCtxRef.current.currentTime, 1.5)
    }, 4000)
  }

  // ── Data polling ─────────────────────────────────────────────────
  useEffect(() => {
    ensureAudioContext()

    let lastSurpriseAt = ''

    async function poll(vol, isMuted) {
      const ctrl = new AbortController()
      abortRef.current = ctrl
      try {
        const [bodyRes, surpriseRes] = await Promise.all([
          fetch('/mc/body-state', { signal: ctrl.signal }).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch('/mc/surprise-state', { signal: ctrl.signal }).then(r => r.ok ? r.json() : null).catch(() => null),
        ])

        const energyLevel = bodyRes?.energy_level || 'default'
        currentEnergyRef.current = energyLevel
        applyEnergyState(energyLevel, vol, isMuted)

        const surpriseAt = surpriseRes?.generated_at || ''
        if (surpriseAt && surpriseAt !== lastSurpriseAt) {
          try {
            const then = new Date(surpriseAt).getTime()
            if (Date.now() - then < 30_000) {
              triggerSurpriseSilence(vol, isMuted)
              lastSurpriseAt = surpriseAt
            }
          } catch (_) {}
        }
      } catch (_) {}
    }

    // Capture current values for the closure
    const vol = volume
    const isMuted = muted

    poll(vol, isMuted)
    const interval = setInterval(() => poll(vol, isMuted), POLL_INTERVAL_MS)

    return () => {
      clearInterval(interval)
      if (abortRef.current) abortRef.current.abort()
      if (surpriseTimerRef.current) { clearTimeout(surpriseTimerRef.current); surpriseTimerRef.current = null }
      if (oscRef.current) { try { oscRef.current.stop() } catch (_) {} }
      if (audioCtxRef.current) { try { audioCtxRef.current.close() } catch (_) {} }
      audioCtxRef.current = null
      oscRef.current = null
      filterRef.current = null
      gainRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Mute/volume updates ──────────────────────────────────────────
  useEffect(() => {
    const gain = gainRef.current
    const ctx = audioCtxRef.current
    if (!gain || !ctx) return
    const energy = currentEnergyRef.current
    const params = ENERGY_MAP[energy] || ENERGY_MAP.default
    const target = muted ? 0 : volume * params.gain
    gain.gain.setTargetAtTime(target, ctx.currentTime, 0.5)
    savePrefs({ muted, volume })
  }, [muted, volume])

  // ── Controls ─────────────────────────────────────────────────────
  function handleMuteToggle() {
    ensureAudioContext()
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    setMuted(m => !m)
  }

  function handleVolumeChange(e) {
    ensureAudioContext()
    if (audioCtxRef.current?.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    setVolume(parseFloat(e.target.value))
  }

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 12,
        right: 12,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        background: 'rgba(0,0,0,0.45)',
        backdropFilter: 'blur(8px)',
        borderRadius: 20,
        padding: '4px 10px',
        zIndex: 9999,
        fontSize: 11,
        color: 'rgba(255,255,255,0.6)',
      }}
    >
      <button
        onClick={handleMuteToggle}
        title={muted ? 'Slå lyd til' : 'Slå lyd fra'}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0, display: 'flex', alignItems: 'center' }}
      >
        {muted ? <VolumeX size={14} /> : <Volume2 size={14} />}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volume}
        onChange={handleVolumeChange}
        style={{ width: 60, accentColor: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}
        title="Lydstyrke"
      />
    </div>
  )
}
