import { useEffect, useRef, useState } from 'react'
import { Pressable, StyleSheet, Text, View } from 'react-native'
import { useI18n } from '../i18n/I18nContext'
import type { LocaleChoice } from '../i18n/i18n'
import { setAccountLanguage } from '../lib/apiClient'
import type { ApiConfig } from '../lib/types'
import { useStyles, type Theme } from '../theme/ThemeContext'

const OPTIONS: LocaleChoice[] = ['da', 'en', 'auto']

export function LanguageSection({
  config,
  currentLanguage,
}: {
  config: ApiConfig | null
  currentLanguage?: string | null
}) {
  const styles = useStyles(makeStyles)
  const { locale, setLocale, t } = useI18n()
  const [saved, setSaved] = useState(false)
  const savedTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (savedTimer.current) clearTimeout(savedTimer.current)
  }, [])

  useEffect(() => {
    if (currentLanguage === 'da' || currentLanguage === 'en' || currentLanguage === 'auto') {
      setLocale(currentLanguage)
    }
  }, [currentLanguage, setLocale])

  const pick = async (next: LocaleChoice) => {
    setLocale(next)
    if (!config) return
    await setAccountLanguage(config, next)
    setSaved(true)
    if (savedTimer.current) clearTimeout(savedTimer.current)
    savedTimer.current = setTimeout(() => setSaved(false), 1600)
  }

  return (
    <>
      <Text style={styles.sectionTitle}>{t('settings.language')}</Text>
      <View style={styles.card}>
        <Text style={styles.muted}>{t('settings.language.hint')}</Text>
        <View style={styles.row}>
          {OPTIONS.map((option) => {
            const on = locale === option
            return (
              <Pressable
                key={option}
                accessibilityRole="button"
                accessibilityState={{ selected: on }}
                onPress={() => void pick(option)}
                style={({ pressed }) => [styles.chip, on && styles.chipOn, pressed && styles.pressed]}
              >
                <Text style={[styles.chipText, on && styles.chipTextOn]}>
                  {t(`settings.language.${option}`)}
                </Text>
              </Pressable>
            )
          })}
        </View>
        {saved ? <Text style={styles.saved}>{t('settings.saved')}</Text> : null}
      </View>
    </>
  )
}

const makeStyles = (tokens: Theme) => StyleSheet.create({
  sectionTitle: {
    color: tokens.color.fg3,
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    marginTop: tokens.spacing.md,
    marginBottom: tokens.spacing.xs,
  },
  card: {
    backgroundColor: tokens.color.bg1,
    borderRadius: tokens.radius.lg,
    padding: tokens.spacing.md,
    borderWidth: 1,
    borderColor: tokens.color.line,
    gap: tokens.spacing.sm,
  },
  muted: { color: tokens.color.fg3 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: tokens.spacing.sm },
  chip: {
    borderWidth: 1,
    borderColor: tokens.color.line,
    borderRadius: 999,
    paddingVertical: 8,
    paddingHorizontal: 14,
  },
  chipOn: { backgroundColor: tokens.color.accent, borderColor: tokens.color.accent },
  chipText: { color: tokens.color.fg2, fontWeight: '600' },
  chipTextOn: { color: tokens.color.bg0, fontWeight: '800' },
  saved: { color: tokens.color.accentText, fontWeight: '700' },
  pressed: { opacity: 0.7 },
})
