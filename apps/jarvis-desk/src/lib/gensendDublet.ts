/**
 * Gensend på en bruger-boble (Bjørn: «to identiske beskeder»).
 *
 * Gensend sender teksten som en NY besked via den almindelige send-vej. Den
 * gamle boble blev derfor stående, og transcriptet viste to ens bobler.
 * Den gamle markeres som «erstattet» og skjules i visningen; den nye står
 * tilbage som den ene.
 */
interface Raekke { id: string }

export function udenErstattede<T extends Raekke>(
  beskeder: readonly T[],
  erstattede: ReadonlySet<string>,
): readonly T[] {
  if (erstattede.size === 0) return beskeder
  return beskeder.some((m) => erstattede.has(m.id))
    ? beskeder.filter((m) => !erstattede.has(m.id))
    : beskeder
}
