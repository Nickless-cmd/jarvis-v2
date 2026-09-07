import * as Haptics from 'expo-haptics'

/** Haptisk kvittering på de handlinger der har konsekvenser.
 *
 *  Ikke på alt. En vibration ved hvert tryk bliver til støj man slår fra, og
 *  så mister man den også dér hvor den betyder noget. Tre steder:
 *
 *    send     — beskeden er afsted (let)
 *    stop     — du afbrød ham midt i noget (tungere; det er et indgreb)
 *    godkend  — du gav ham lov til at ændre noget (succes-mønster)
 *    afvis    — du sagde nej (advarsel-mønster, så de to ikke føles ens)
 *
 *  Alt fejler stille: en enhed uden vibrator, en emulator eller en bruger der
 *  har slået haptik fra i systemet må aldrig kunne vælte en send-knap.
 */

export type HaptiskHandling = 'send' | 'stop' | 'godkend' | 'afvis' | 'fejl'

export async function haptik(handling: HaptiskHandling): Promise<void> {
  try {
    switch (handling) {
      case 'send':
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light)
        return
      case 'stop':
        await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium)
        return
      case 'godkend':
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)
        return
      case 'afvis':
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning)
        return
      case 'fejl':
        await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)
        return
    }
  } catch {
    /* stille — haptik er en kvittering, ikke en funktion */
  }
}
