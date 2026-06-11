/** Placeholder — rolle-skopet. Member ser egne planlagte; owner ser alle.
 *  Server-kontrakt defineres i Scheduling-spec. */
export function SchedulingView({ role }: { role: 'owner' | 'member' | 'guest' }) {
  return (
    <div className="view-placeholder">
      <h2>Scheduling</h2>
      <p>{role === 'owner' ? 'Alle planlagte tasks (kommer)' : 'Hvad Jarvis har planlagt med dig (kommer)'}</p>
    </div>
  )
}
