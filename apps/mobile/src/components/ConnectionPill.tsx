import { StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export function ConnectionPill({ label }: { label: string }) {
  return (
    <View style={styles.root}>
      <Text style={styles.text}>{label}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    paddingHorizontal: tokens.spacing.sm,
    paddingVertical: tokens.spacing.xs,
    borderRadius: tokens.radius.lg,
    backgroundColor: tokens.color.bg2,
    borderWidth: 1,
    borderColor: tokens.color.line
  },
  text: {
    color: tokens.color.fg2,
    fontSize: 12,
    fontWeight: '600'
  }
})
