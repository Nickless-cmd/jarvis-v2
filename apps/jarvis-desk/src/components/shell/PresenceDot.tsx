import { JarvisRing } from './JarvisRing'

/** Header presence follows the same stream state and Puls mark as the composer. */
export function PresenceDot({ status }: { status: string }) {
  const tone = status === 'working' ? 'working' : status === 'error' || status === 'interrupted' ? 'error' : 'idle'
  const label = tone === 'working' ? 'Jarvis arbejder…' : tone === 'error' ? 'Afbrudt' : 'Jarvis'
  return (
    <span className="puls-presence" title={label} aria-label={label}>
      <JarvisRing size={18} spinning={tone === 'working'} tone={tone} />
    </span>
  )
}
