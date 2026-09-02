import { useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { tokens } from '../theme/tokens'

export interface ApprovalViewModel {
  approvalId: string
  tool: string
  message: string
  detail?: string
}

// Kortets indhold får et loft, så knapperne aldrig kan skubbes ud af skærmen.
// Bjørn 21. aug 2026: "teksten i hans approval cards bliver for stor til skærmen
// så jeg ikk kan trykke tillad". `detail` er hele kommandoen — for et bash-kald
// kan det være hundredvis af tegn med heredocs og pipes — og den blev renderet
// helt uden begrænsning. Kortet voksede til under skærmkanten, og godkendelse
// blev fysisk umulig. Runnet døde så af approval-timeout uden at han kunne gøre
// noget ved det.
const CONTENT_MAX_HEIGHT = 220
// Hvor mange linjer af kommandoen der vises før "Vis alt". Nok til at man kan se
// hvad man siger ja til, lidt nok til at knapperne bliver siddende.
const DETAIL_PREVIEW_LINES = 6

export function ApprovalCard({
  approval,
  onApprove,
  onDeny
}: {
  approval: ApprovalViewModel
  onApprove: () => void
  onDeny: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const detail = approval.detail ?? ''
  // Kun tilbyd udvidelse når der faktisk er noget skjult — ellers er knappen støj.
  const isLong = detail.length > 160 || detail.split('\n').length > DETAIL_PREVIEW_LINES

  return (
    <View style={styles.root}>
      <Text style={styles.title}>{approval.tool || 'Approval required'}</Text>
      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentInner}
        nestedScrollEnabled
      >
        <Text style={styles.message}>{approval.message}</Text>
        {detail ? (
          <Text
            style={styles.detail}
            numberOfLines={expanded ? undefined : DETAIL_PREVIEW_LINES}
          >
            {detail}
          </Text>
        ) : null}
      </ScrollView>
      {isLong ? (
        <Pressable
          accessibilityRole="button"
          onPress={() => setExpanded((v) => !v)}
          style={styles.expandRow}
        >
          <Text style={styles.expandText}>{expanded ? 'Vis mindre' : 'Vis alt'}</Text>
        </Pressable>
      ) : null}
      {/* Uden for ScrollView'en: knapperne skal være nåelige uanset indholdets længde. */}
      <View style={styles.actions}>
        <Pressable accessibilityRole="button" onPress={onDeny} style={[styles.button, styles.deny]}>
          <Text style={styles.buttonText}>Afvis</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          onPress={onApprove}
          style={[styles.button, styles.allow]}
        >
          <Text style={styles.allowText}>Tillad</Text>
        </Pressable>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    margin: tokens.spacing.md,
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md,
    borderWidth: 1,
    borderColor: tokens.color.warn,
    backgroundColor: tokens.color.bg1
  },
  title: {
    color: tokens.color.fg1,
    fontWeight: '700',
    marginBottom: tokens.spacing.xs
  },
  content: {
    maxHeight: CONTENT_MAX_HEIGHT
  },
  contentInner: {
    paddingRight: tokens.spacing.xs
  },
  message: {
    color: tokens.color.fg2
  },
  detail: {
    color: tokens.color.fg3,
    marginTop: tokens.spacing.sm,
    fontFamily: 'monospace'
  },
  expandRow: {
    paddingVertical: tokens.spacing.xs
  },
  expandText: {
    color: tokens.color.accent,
    fontWeight: '600'
  },
  actions: {
    flexDirection: 'row',
    gap: tokens.spacing.sm,
    marginTop: tokens.spacing.md
  },
  button: {
    flex: 1,
    alignItems: 'center',
    padding: tokens.spacing.md,
    borderRadius: tokens.radius.md
  },
  deny: {
    backgroundColor: tokens.color.bg3
  },
  allow: {
    backgroundColor: tokens.color.accent
  },
  buttonText: {
    color: tokens.color.fg1,
    fontWeight: '700'
  },
  allowText: {
    color: tokens.color.bg0,
    fontWeight: '700'
  }
})
