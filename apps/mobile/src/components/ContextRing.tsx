import Svg, { Circle } from 'react-native-svg'
import { View } from 'react-native'
import { useTheme } from '../theme/ThemeContext'
import type { ContextUsage } from '../lib/apiClient'

/**
 * Hvor fuld konteksten er, som en lille ring i headerens højre felt.
 *
 * ## Hvorfor den står dér
 *
 * Bjørn bad om «en context ring lige før de tre prikker i samme badge». Det er
 * det ene tal man vil kunne se uden at åbne noget, fordi det er dét der
 * afgør om samtalen snart bliver komprimeret — og en komprimering man ikke så
 * komme, ligner hukommelsestab.
 *
 * ## Hvorfor den er tavs indtil den ikke er det
 *
 * Under halvvejs tegnes den i dæmpet farve. Det er ikke pynt: en ring der
 * skriger fra 5 % lærer én at se bort fra den, og så virker den heller ikke
 * ved 90 %.
 */
export function ContextRing({
  brug, size = 22, tykkelse = 2.5,
}: { brug: ContextUsage | null; size?: number; tykkelse?: number }) {
  const tokens = useTheme()
  const andel = kontekstAndel(brug)
  if (andel === null) return null

  const r = (size - tykkelse) / 2
  const omkreds = 2 * Math.PI * r
  const farve = andel >= 0.85 ? tokens.color.warn
    : andel >= 0.6 ? tokens.color.accent
    : tokens.color.fg2

  return (
    <View
      testID="context-ring"
      accessibilityLabel={`Kontekst ${Math.round(andel * 100)} procent fuld`}
    >
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2} cy={size / 2} r={r}
          stroke={tokens.color.bg2} strokeWidth={tykkelse} fill="none"
        />
        <Circle
          testID="context-ring-bue"
          cx={size / 2} cy={size / 2} r={r}
          stroke={farve} strokeWidth={tykkelse} fill="none"
          strokeDasharray={`${omkreds}`}
          strokeDashoffset={omkreds * (1 - andel)}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
    </View>
  )
}

/**
 * Andelen af konteksten der er brugt — eller null når der intet er at vise.
 *
 * `null` frem for 0 af samme grund som i `samletUploadAndel`: en tom ring og
 * INGEN ring betyder to forskellige ting, og «vi har ikke spurgt endnu» må
 * ikke se ud som «samtalen er tom».
 *
 * Nævneren er `compactAt` og ikke modellens fulde vindue. Det er dér
 * komprimeringen fyrer, og det er DEN begivenhed ringen advarer om — en ring
 * mod det fulde vindue ville stå på 40 % i samme øjeblik samtalen blev
 * komprimeret, og så ville den lyve om præcis det den findes for.
 */
export function kontekstAndel(brug: ContextUsage | null | undefined): number | null {
  if (!brug) return null
  const naevner = Number(brug.compactAt)
  // Et nul-nævner er ikke «0 %», det er «serveren sagde ikke hvor grænsen gaar».
  if (!Number.isFinite(naevner) || naevner <= 0) return null
  const t = Number(brug.tokens)
  if (!Number.isFinite(t) || t < 0) return null
  return Math.max(0, Math.min(1, t / naevner))
}
