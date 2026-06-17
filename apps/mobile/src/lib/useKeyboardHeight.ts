import { useEffect, useState } from 'react'
import { Keyboard } from 'react-native'

/**
 * Returnerer tastaturets aktuelle højde i px (0 når skjult).
 *
 * Hvorfor ikke KeyboardAvoidingView: i edge-to-edge-tilstand (Android 15/16,
 * Expo-default) krymper app-vinduet IKKE når IME'en vises — vinduet bliver
 * fuld højde og tastaturet tegnes ovenpå. Så KeyboardAvoidingViews
 * frame-baserede beregning løfter ikke composeren. I stedet padder vi
 * indholdet op med den faktiske tastaturhøjde fra Keyboard-eventet.
 */
export function useKeyboardHeight(): number {
  const [height, setHeight] = useState(0)

  useEffect(() => {
    // 'Did'-eventene er dem Android leverer pålideligt med adjustResize.
    const show = Keyboard.addListener('keyboardDidShow', (e) => {
      setHeight(e.endCoordinates?.height ?? 0)
    })
    const hide = Keyboard.addListener('keyboardDidHide', () => setHeight(0))
    return () => {
      show.remove()
      hide.remove()
    }
  }, [])

  return height
}
