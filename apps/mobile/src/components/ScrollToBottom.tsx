import { useEffect, useRef } from 'react'
import { Animated, Pressable, StyleSheet } from 'react-native'
import { ChevronDown } from 'lucide-react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/**
 * Rul-til-bunden — målt i ChatGPT-appen: en lille mørk cirkel med en pil ned,
 * centreret lige over komponisten. Den dukker op når man har rullet OP i
 * tråden, og forsvinder igen når man er nede ved det nyeste.
 *
 * Den erstatter Save Rail'en i højre side. Forskellen er ikke pynt: rail'en
 * kom frem ved AL scroll-aktivitet — også når man allerede var i bunden, hvor
 * der ikke er noget at hoppe til. Den her kommer kun frem når den har et svar
 * på et spørgsmål man faktisk kan have («hvor er det nyeste?»).
 */
export function ScrollToBottom({ visible, bottom, onPress }: {
  visible: boolean
  /** Afstand fra bunden — sættes så knappen står lige over komponisten. */
  bottom: number
  onPress: () => void
}) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const fade = useRef(new Animated.Value(0)).current

  useEffect(() => {
    Animated.timing(fade, {
      toValue: visible ? 1 : 0,
      duration: 160,
      useNativeDriver: true
    }).start()
  }, [visible, fade])

  return (
    <Animated.View
      pointerEvents={visible ? 'box-none' : 'none'}
      style={[styles.wrap, { bottom, opacity: fade }]}
    >
      <Pressable
        testID="scroll-to-bottom"
        accessibilityRole="button"
        accessibilityLabel="Rul til nyeste"
        onPress={onPress}
        hitSlop={8}
        style={({ pressed }) => [styles.circle, pressed && styles.pressed]}
      >
        <ChevronDown size={20} color={tokens.color.fg1} strokeWidth={2.2} />
      </Pressable>
    </Animated.View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: {
    position: 'absolute',
    left: 0,
    right: 0,
    alignItems: 'center',
    zIndex: 6
  },
  circle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: tokens.color.bg2,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: tokens.color.line
  },
  pressed: { opacity: 0.7 }
})
