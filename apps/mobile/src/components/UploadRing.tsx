import Svg, { Circle } from 'react-native-svg'
import { View } from 'react-native'
import { useTheme } from '../theme/ThemeContext'

/**
 * Ring der fyldes i takt med en upload.
 *
 * ## Hvorfor den findes
 *
 * Fremdriften blev målt hele tiden — `uploadAttachment` kalder tilbage med en
 * brøkdel, og komponisten viste den som et lille tal på miniaturen. Men den
 * store knap nederst til højre blev ved med at være bølge-ikonet, og det er
 * den knap øjet hviler på. Bjørn: «ellers virker det bare som om appen
 * hænger».
 *
 * Så tallet fandtes; det stod bare et sted ingen kigger mens de venter.
 *
 * ## Hvorfor en ring og ikke en spinner
 *
 * En spinner siger «noget sker» og lyver om at den ved hvor længe. En ring der
 * fyldes siger hvor langt man er — og det er forskellen på at vente og at
 * være i tvivl om appen er død.
 */
export function UploadRing({
  andel, size = 44, tykkelse = 3,
}: { andel: number; size?: number; tykkelse?: number }) {
  const tokens = useTheme()
  // Klem til [0,1]. En andel over 1 ville tegne buen forbi sig selv, og under
  // 0 ville give en negativ omkreds — begge dele ser ud som en fejl i UI'et
  // frem for i det der leverede tallet.
  const a = Math.max(0, Math.min(1, Number.isFinite(andel) ? andel : 0))
  const r = (size - tykkelse) / 2
  const omkreds = 2 * Math.PI * r
  return (
    <View testID="upload-ring" accessibilityLabel={`Uploader ${Math.round(a * 100)} procent`}>
      <Svg width={size} height={size}>
        {/* Sporet. Uden det ser en ring paa 10% ud som en tilfaeldig streg. */}
        <Circle
          cx={size / 2} cy={size / 2} r={r}
          stroke={tokens.color.bg2} strokeWidth={tykkelse} fill="none"
        />
        <Circle
          testID="upload-ring-bue"
          cx={size / 2} cy={size / 2} r={r}
          stroke={tokens.color.accent} strokeWidth={tykkelse} fill="none"
          strokeDasharray={`${omkreds}`}
          // Fuld offset = tom ring. Trukket fra, saa 0 % tegner ingenting og
          // 100 % tegner hele cirklen.
          strokeDashoffset={omkreds * (1 - a)}
          strokeLinecap="round"
          // Start i toppen. Uden rotationen begynder buen paa hoejre side, og
          // en ring der fyldes fra klokken 3 laeses som en fejl.
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
    </View>
  )
}

/**
 * Samlet fremdrift for de vedhæftninger der stadig uploader.
 *
 * Gennemsnit frem for «den første» eller «den mindste»: sender man tre filer,
 * er det den samlede ventetid man mærker. Er ingen i gang, returneres null —
 * så kalderen kan se forskel på «ingen upload» og «upload på 0 %».
 */
export function samletUploadAndel(
  vedhaeftninger: { status?: string; progress?: number }[] | undefined,
): number | null {
  const igang = (vedhaeftninger || []).filter((a) => a.status === 'uploading')
  if (!igang.length) return null
  const sum = igang.reduce((n, a) => n + Math.max(0, Math.min(1, Number(a.progress) || 0)), 0)
  return sum / igang.length
}
