/**
 * Serverens grund til at afvise en upload — vist som den er.
 *
 * Serveren afviser med en KONKRET begrundelse: «Arkivet blev afvist: sti peger
 * opad (..)», «Upload afvist af malware-scan: Eicar-Test-Signature». Første
 * udgave viste «Kunne ikke uploade billedet — prøv igen», og så prøvede man
 * igen med præcis samme fil og fik præcis samme svar. En afvisning man ikke
 * kan handle på, er værre end ingen.
 */
export function describeUploadError(err: unknown): string {
  const detail = extractDetail(err)
  return detail ? ` — ${detail}` : ''
}

function extractDetail(err: unknown): string {
  if (!err) return ''
  if (typeof err === 'string') return err.trim()
  const anyErr = err as { detail?: unknown; message?: unknown }
  const raw = String(anyErr.detail ?? anyErr.message ?? '').trim()
  if (!raw) return ''
  // Fejl fra fetch-laget bærer ofte hele svaret som JSON i message.
  try {
    const parsed = JSON.parse(raw)
    const d = (parsed as { detail?: unknown })?.detail
    if (typeof d === 'string' && d.trim()) return d.trim()
  } catch {
    // ikke JSON — brug teksten som den er
  }
  return raw
}
