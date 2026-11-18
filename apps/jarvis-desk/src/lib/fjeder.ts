export interface FjederParametre {
  stiffness: number
  damping: number
  mass?: number
  velocity?: number
}

export interface Fjederkurve {
  durationMs: number
  vaerdier: number[]
}

const SAMPLE_ANTAL = 61
const MAKS_VARIGHED_SEKUNDER = 10
const STABIL_PERIODE_SEKUNDER = 0.05
const POSITION_TOLERANCE = 0.01
const HASTIGHED_TOLERANCE = 0.15

function valider({ stiffness, damping, mass = 1, velocity = 0 }: FjederParametre): void {
  if (!Number.isFinite(stiffness) || stiffness <= 0) {
    throw new Error(`Spring animation stiffness must be greater than 0. Provided: ${stiffness}`)
  }
  if (!Number.isFinite(damping) || damping <= 0) {
    throw new Error(`Spring animation damping must be greater than 0. Provided: ${damping}`)
  }
  if (!Number.isFinite(mass) || mass <= 0) {
    throw new Error(`Spring animation mass must be greater than 0. Provided: ${mass}`)
  }
  if (!Number.isFinite(velocity)) {
    throw new Error(`Spring animation velocity must be finite. Provided: ${velocity}`)
  }
}

function tilstandVed(
  tid: number,
  { stiffness, damping, mass = 1, velocity = 0 }: FjederParametre,
): { position: number; velocity: number } {
  const omega0 = Math.sqrt(stiffness / mass)
  const zeta = damping / (2 * Math.sqrt(stiffness * mass))
  const startAfvigelse = -1

  if (zeta < 1 - 1e-7) {
    const omegaD = omega0 * Math.sqrt(1 - zeta * zeta)
    const a = startAfvigelse
    const b = (velocity + zeta * omega0 * a) / omegaD
    const envelope = Math.exp(-zeta * omega0 * tid)
    const cos = Math.cos(omegaD * tid)
    const sin = Math.sin(omegaD * tid)
    const afvigelse = envelope * (a * cos + b * sin)
    const fart = envelope * (
      -zeta * omega0 * (a * cos + b * sin)
      + omegaD * (-a * sin + b * cos)
    )
    return { position: 1 + afvigelse, velocity: fart }
  }

  if (Math.abs(zeta - 1) <= 1e-7) {
    const a = startAfvigelse
    const b = velocity + omega0 * a
    const envelope = Math.exp(-omega0 * tid)
    const afvigelse = (a + b * tid) * envelope
    const fart = (b - omega0 * (a + b * tid)) * envelope
    return { position: 1 + afvigelse, velocity: fart }
  }

  const rod = Math.sqrt(zeta * zeta - 1)
  const r1 = -omega0 * (zeta - rod)
  const r2 = -omega0 * (zeta + rod)
  const c1 = (velocity - startAfvigelse * r2) / (r1 - r2)
  const c2 = startAfvigelse - c1
  const e1 = Math.exp(r1 * tid)
  const e2 = Math.exp(r2 * tid)
  return {
    position: 1 + c1 * e1 + c2 * e2,
    velocity: c1 * r1 * e1 + c2 * r2 * e2,
  }
}

function findVarighed(parametre: FjederParametre): number {
  let stabilFra: number | null = null
  for (let tid = 0; tid <= MAKS_VARIGHED_SEKUNDER; tid += 0.001) {
    const tilstand = tilstandVed(tid, parametre)
    const stabil = Math.abs(1 - tilstand.position) <= POSITION_TOLERANCE
      && Math.abs(tilstand.velocity) <= HASTIGHED_TOLERANCE
    if (!stabil) {
      stabilFra = null
    } else if (stabilFra === null) {
      stabilFra = tid
    } else if (tid - stabilFra >= STABIL_PERIODE_SEKUNDER) {
      return tid
    }
  }
  return MAKS_VARIGHED_SEKUNDER
}

/** Beregner den dæmpede step-response fra 0 til 1 som jævnt fordelte samples. */
export function beregnFjederkurve(parametre: FjederParametre): Fjederkurve {
  valider(parametre)
  const varighedSekunder = findVarighed(parametre)
  const vaerdier = Array.from({ length: SAMPLE_ANTAL }, (_, indeks) => {
    if (indeks === 0) return 0
    if (indeks === SAMPLE_ANTAL - 1) return 1
    const tid = varighedSekunder * indeks / (SAMPLE_ANTAL - 1)
    return Number(tilstandVed(tid, parametre).position.toFixed(5))
  })
  return { durationMs: Math.round(varighedSekunder * 1000), vaerdier }
}

/** CSS Easing Level 2: samples er jævnt fordelt, så `linear()` kan afspille fysikken. */
export function fjederTilCss(parametre: FjederParametre): { durationMs: number; easing: string } {
  const kurve = beregnFjederkurve(parametre)
  return {
    durationMs: kurve.durationMs,
    easing: `linear(${kurve.vaerdier.join(', ')})`,
  }
}
