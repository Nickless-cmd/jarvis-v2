import { StyleSheet, View } from 'react-native'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

export function JarvisRing() {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  return (
    <View style={styles.outer}>
      <View style={styles.inner} />
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  outer: {
    width: 28,
    height: 28,
    borderRadius: 14,
    borderWidth: 2,
    borderColor: tokens.color.accent,
    alignItems: 'center',
    justifyContent: 'center'
  },
  inner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: tokens.color.accent
  }
})
