import { useCallback, useEffect, useState } from 'react'
import { ActivityIndicator, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native'
import { HardDrive, Monitor, Pause, Play, Square } from 'lucide-react-native'
import { hentJobs, jobHandling, type BaggrundsJob } from '../lib/jobsApi'
import { formatVarighed } from '../lib/runResume'
import type { ApiConfig } from '../lib/types'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

/** Tre sekunder. Se `useEffect` nedenfor for hvorfor klienten ikke tæller selv. */
const PULS_MS = 3_000

/**
 * Hvad kører lige nu?
 *
 * ## Hvorfor tiden kommer fra serveren hver gang
 *
 * Klienten kunne tælle sekunder selv mellem opslag, og tallet ville se mere
 * levende ud. Men så er der to ure, og to ure driver fra hinanden — desk
 * traf det samme valg med samme begrundelse. I stedet spørges der hvert
 * tredje sekund, og tallet er altid serverens.
 *
 * ## Hvorfor panelet må være tomt
 *
 * En opgave der lykkedes forsvinder. Én der fejlede bliver stående, for den
 * er ikke fuldført — den gik galt, og det er netop dem man skal se. Et panel
 * der altid har noget i sig bliver et panel man holder op med at åbne.
 */
export function JobsPanel({
  aaben, onClose, config,
}: { aaben: boolean; onClose: () => void; config: ApiConfig }) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const [jobs, setJobs] = useState<BaggrundsJob[] | null>(null)
  const [broOk, setBroOk] = useState(true)
  const [travl, setTravl] = useState<string>('')

  const hent = useCallback(async () => {
    try {
      const s = await hentJobs(config)
      setJobs(s.jobs)
      setBroOk(s.broOk)
    } catch {
      setJobs([])
      setBroOk(false)
    }
  }, [config])

  useEffect(() => {
    if (!aaben) return
    void hent()
    const t = setInterval(() => { void hent() }, PULS_MS)
    return () => clearInterval(t)
  }, [aaben, hent])

  const gør = async (job: BaggrundsJob, h: 'pause' | 'resume' | 'stop') => {
    setTravl(job.id)
    try {
      await jobHandling(config, job, h)
      // Hent MED DET SAMME frem for at vente på næste puls: et tryk der først
      // ser ud til at virke tre sekunder senere, læses som et tryk der ikke
      // virkede.
      await hent()
    } catch {
      await hent()
    } finally {
      setTravl('')
    }
  }

  return (
    <Modal transparent visible={aaben} animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.scrim} onPress={onClose}>
        <Pressable style={styles.ark} onPress={(e) => e.stopPropagation()}>
          <View style={styles.greb} />
          <Text style={styles.titel}>Baggrundsjobs</Text>

          {!broOk ? (
            // «Vi ved det ikke» er ikke det samme som «der er ingenting».
            <Text style={styles.advarsel} testID="jobs-bro-nede">
              Kunne ikke spørge din computer — der kan køre noget dér som ikke står her.
            </Text>
          ) : null}

          {jobs === null ? (
            <ActivityIndicator size="small" color={tokens.color.fg2} style={styles.spinner} />
          ) : jobs.length === 0 ? (
            <Text style={styles.tom} testID="jobs-tom">Ingenting kører lige nu.</Text>
          ) : (
            <ScrollView style={styles.liste}>
              {jobs.map((j) => (
                <View key={`${j.kilde}-${j.id}`} testID={`job-${j.id}`} style={styles.raekke}>
                  <View style={styles.hvor}>
                    {j.kilde === 'operator'
                      ? <Monitor size={15} color={tokens.color.fg2} strokeWidth={1.8} />
                      : <HardDrive size={15} color={tokens.color.fg2} strokeWidth={1.8} />}
                  </View>
                  <View style={styles.midt}>
                    <Text style={styles.navn} numberOfLines={1}>{j.navn}</Text>
                    <Text style={styles.kommando} numberOfLines={1}>{j.kommando}</Text>
                  </View>
                  <Text style={[styles.tid, j.status === 'paused' ? styles.tidPause : null]}>
                    {j.status === 'exited'
                      ? `stop ${j.exitCode ?? ''}`.trim()
                      : formatVarighed(j.sekunder)}
                  </Text>
                  {j.kanPause ? (
                    <Pressable
                      testID={`job-${j.status === 'paused' ? 'resume' : 'pause'}-${j.id}`}
                      accessibilityRole="button"
                      accessibilityLabel={j.status === 'paused' ? `Genoptag ${j.navn}` : `Pause ${j.navn}`}
                      disabled={travl === j.id}
                      onPress={() => void gør(j, j.status === 'paused' ? 'resume' : 'pause')}
                      hitSlop={6}
                      style={styles.knap}
                    >
                      {j.status === 'paused'
                        ? <Play size={15} color={tokens.color.fg1} strokeWidth={2} />
                        : <Pause size={15} color={tokens.color.fg1} strokeWidth={2} />}
                    </Pressable>
                  ) : null}
                  <Pressable
                    testID={`job-stop-${j.id}`}
                    accessibilityRole="button"
                    accessibilityLabel={`Stop ${j.navn}`}
                    disabled={travl === j.id}
                    onPress={() => void gør(j, 'stop')}
                    hitSlop={6}
                    style={styles.knap}
                  >
                    <Square size={13} color={tokens.color.warn} strokeWidth={2.4} />
                  </Pressable>
                </View>
              ))}
            </ScrollView>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  scrim: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  ark: {
    maxHeight: '75%',
    backgroundColor: tokens.color.bg1,
    borderTopLeftRadius: 18, borderTopRightRadius: 18,
    paddingBottom: 24, paddingTop: 8, paddingHorizontal: tokens.spacing.sm,
  },
  greb: {
    alignSelf: 'center', width: 36, height: 4, borderRadius: 2,
    backgroundColor: tokens.color.bg2, marginBottom: 10,
  },
  titel: {
    color: tokens.color.fg1, fontSize: 15, fontWeight: '600',
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 8,
  },
  advarsel: {
    color: tokens.color.warn, fontSize: 12,
    paddingHorizontal: tokens.spacing.sm, paddingBottom: 8,
  },
  liste: { maxHeight: 420 },
  raekke: {
    flexDirection: 'row', alignItems: 'center', gap: 9,
    paddingVertical: 10, paddingHorizontal: tokens.spacing.sm,
  },
  hvor: { width: 18, alignItems: 'center' },
  midt: { flex: 1 },
  navn: { color: tokens.color.fg1, fontSize: 14 },
  kommando: { color: tokens.color.fg2, fontSize: 11 },
  tid: {
    color: tokens.color.fg2, fontSize: 12,
    fontVariant: ['tabular-nums'], minWidth: 62, textAlign: 'right',
  },
  tidPause: { color: tokens.color.warn },
  knap: {
    width: 30, height: 30, borderRadius: 15,
    backgroundColor: tokens.color.bg2, alignItems: 'center', justifyContent: 'center',
  },
  tom: { color: tokens.color.fg2, fontSize: 13, padding: tokens.spacing.sm },
  spinner: { paddingVertical: 20 },
})
