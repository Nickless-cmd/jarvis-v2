import { useEffect, useRef, useState } from 'react'
import { Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { Check, Copy } from 'lucide-react-native'
import * as Clipboard from 'expo-clipboard'
import { highlight, type SpanKind } from '../lib/highlight'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

const MONO = Platform.select({ ios: 'Menlo', android: 'monospace', default: 'monospace' })

/**
 * Kodeblok — bygget efter ChatGPT-appen (set 2026-09-02).
 *
 * Tre ting deres har, som vores ikke havde: en afrundet flade der er LYSERE
 * end siden, syntaksfarver, og en kopiér-knap inde i blokken øverst til højre.
 *
 * Kopiér-knappen er den vigtigste. Kode i en chat er noget man skal have UD
 * af chatten, og uden knappen skal man markere tekst med fingeren i en flade
 * der ruller vandret — det virker næsten aldrig i første forsøg.
 *
 * Blokken ruller vandret i sin EGEN beholder. Lange linjer må aldrig kunne
 * skubbe hele tråden sidelæns.
 */
export function CodeBlock({ code, language }: { code: string; language?: string }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [copied, setCopied] = useState(false)
  const body = String(code ?? '').replace(/\n$/, '')
  // Timeren ryddes ved unmount: bliver blokken fjernet mens kvitteringen står,
  // ville et setState ellers ramme en komponent der ikke er der længere.
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  const copy = async () => {
    await Clipboard.setStringAsync(body)
    setCopied(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setCopied(false), 1500)
  }

  return (
    <View style={styles.wrap}>
      <View style={styles.bar}>
        <Text style={styles.lang}>{(language || '').trim().toLowerCase()}</Text>
        <Pressable
          testID="code-copy"
          accessibilityRole="button"
          accessibilityLabel={copied ? 'Kopieret' : 'Kopiér kode'}
          hitSlop={10}
          onPress={copy}
          style={({ pressed }) => [styles.copy, pressed && styles.pressed]}
        >
          {copied ? (
            <Check size={15} color={tokens.color.accent} strokeWidth={2.2} />
          ) : (
            <Copy size={15} color={tokens.color.fg2} strokeWidth={1.8} />
          )}
        </Pressable>
      </View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.scroll}>
        <Text style={styles.code}>
          {highlight(body).map((t, i) => (
            <Text key={i} style={COLOR[t.kind]}>{t.text}</Text>
          ))}
        </Text>
      </ScrollView>
    </View>
  )
}

const COLOR: Record<SpanKind, { color: string }> = {
  plain: { color: '#E6EDF3' },
  str: { color: '#7EE787' },
  com: { color: '#6E7681' },
  num: { color: '#FFA657' },
  kw: { color: '#79C0FF' }
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  wrap: {
    backgroundColor: tokens.color.codeBg,
    borderRadius: tokens.radius.lg,
    marginVertical: tokens.spacing.sm,
    overflow: 'hidden',
    // Uden disse to måler den vandrette ScrollView sig efter sit INDHOLD og
    // trak blokken ud over beskedens højremargen — målt på enheden: 1038 px
    // bred i en 996 px spalte, så koden blev klippet af skærmkanten i stedet
    // for at kunne rulles. `width: 100%` binder bredden til spalten; derefter
    // ruller indholdet indeni, som det skal.
    alignSelf: 'stretch',
    width: '100%'
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: tokens.spacing.md,
    paddingTop: tokens.spacing.sm,
    paddingBottom: 2
  },
  lang: { color: tokens.color.fg3, fontSize: 11, fontWeight: '600', letterSpacing: 0.4 },
  copy: { padding: 4 },
  scroll: { paddingHorizontal: tokens.spacing.md, paddingBottom: tokens.spacing.md },
  code: { fontFamily: MONO, fontSize: 13, lineHeight: 19 },
  pressed: { opacity: 0.6 }
})
