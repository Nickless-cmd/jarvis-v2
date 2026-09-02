import { useMemo } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { greetingFor } from '../lib/greeting'
import { tokens } from '../theme/tokens'

/**
 * Tom-session-skærm: tids-bevidst greeting + presence-ring tonet efter
 * tidspunkt (spejlet fra jarvis-desk GreetingHero). Vises når chatten er tom
 * — dvs. ved opstart/ny samtale — og forsvinder så snart der er beskeder.
 */
export function GreetingHero({ userName }: { userName: string }) {
  // Random men stabil pr. mount (varierer mellem opstart — "random greeting").
  const g = useMemo(() => greetingFor(new Date(), Math.floor(Math.random() * 1000)), [])

  return (
    <View style={styles.root}>
      <View style={[styles.ring, { borderColor: g.tint }]}>
        <Text style={styles.glyph}>{g.glyph}</Text>
      </View>
      <Text style={styles.hello}>
        {g.hello}, {userName}
      </Text>
      <Text style={styles.line}>{g.line}</Text>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: tokens.spacing.xl,
    gap: tokens.spacing.md
  },
  ring: {
    width: 88,
    height: 88,
    borderRadius: 44,
    borderWidth: 3,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: tokens.spacing.sm
  },
  glyph: {
    fontSize: 40
  },
  hello: {
    color: tokens.color.fg1,
    fontSize: 24,
    fontWeight: '700',
    textAlign: 'center'
  },
  line: {
    color: tokens.color.fg3,
    fontSize: 16,
    textAlign: 'center'
  }
})
