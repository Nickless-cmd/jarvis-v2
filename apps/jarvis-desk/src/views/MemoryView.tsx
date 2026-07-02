/** Placeholder — rolle-skopet. Member ser relation; owner ser fuld indre memory.
 *  Server-kontrakt defineres i Memory-spec. */
export function MemoryView({ role }: { role: 'owner' | 'member' | 'guest' }) {
  return (
    <div className="view-placeholder">
      <h2>Memory</h2>
      <p>{role === 'owner' ? 'Fuld indre memory (kommer)' : 'Din relation med J.A.R.V.I.S. (kommer)'}</p>
    </div>
  )
}
