import { clampForSpeech, stripForSpeech } from './speechText'

describe('stripForSpeech', () => {
  // Bjoerns klage: oplaesningen citerede tegnene.
  it('laeser ikke stjerner op', () => {
    expect(stripForSpeech('Det er **vigtigt** og *rigtigt*')).toBe('Det er vigtigt og rigtigt')
  })

  it('naevner kodeblokke i stedet for at stave dem', () => {
    const out = stripForSpeech('Kør dette:\n\n```bash\nrm -rf /tmp/x && echo ok\n```\n\nSå er den klar.')
    expect(out).toContain('bash-kode')
    expect(out).not.toContain('rm -rf')
  })

  it('beholder inline-kodens INDHOLD, ikke dens baktikker', () => {
    expect(stripForSpeech('Filen `USER.md` er tom')).toBe('Filen USER.md er tom')
  })

  it('laeser linkets tekst, ikke dets adresse', () => {
    expect(stripForSpeech('Se [rapporten](https://example.com/meget/lang/sti.pdf)'))
      .toBe('Se rapporten')
  })

  it('fjerner listetegn og haveaager, men beholder ordene', () => {
    expect(stripForSpeech('## Overskrift\n- et\n- to\n1. tre')).toBe('Overskrift\net\nto\ntre')
  })

  // Punktummer og kommaer er dét der giver oplaesningen rytme.
  it('roerer ikke almindelig tegnsaetning', () => {
    const s = 'Ja, det passer. Men hvorfor? Fordi — sådan er det.'
    expect(stripForSpeech(s)).toBe(s)
  })

  it('taaler tom og underlig indtastning', () => {
    expect(stripForSpeech('')).toBe('')
    expect(stripForSpeech('   \n\n  ')).toBe('')
  })
})

describe('clampForSpeech', () => {
  it('lader korte tekster vaere', () => {
    expect(clampForSpeech('kort', 100)).toBe('kort')
  })

  // Et afbrudt ord lyder som en fejl; en afsluttet saetning lyder som et valg.
  it('skaerer ved en saetning, ikke midt i et ord', () => {
    const s = 'Første sætning her. Anden sætning som er ret lang og fortsætter et stykke.'
    const out = clampForSpeech(s, 40)
    expect(out.endsWith('.')).toBe(true)
    expect(out).toBe('Første sætning her.')
  })

  it('skaerer haardt hvis der slet ikke er et punktum at gaa efter', () => {
    expect(clampForSpeech('a'.repeat(200), 50)).toHaveLength(50)
  })
})
