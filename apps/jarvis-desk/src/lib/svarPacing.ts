/**
 * Hvornår må den levende tur tegnes — og hvornår skal den persisterede kopi af
 * SAMME run skjules?
 *
 * Baggrund (Bjørn 29/10-2026): «svaret vises to gange i pace-vinduet — én gang
 * som færdig assistent-besked oven over pacen, og den forsvinder når pacen
 * slutter. Den forkerte bliver tilbage.»
 *
 * Mekanikken var at ÉT flag gjorde to job:
 *
 *   const afslutterSvarPacing = status === 'done' && !!activeRunId
 *     && pacedAnswerRunId !== activeRunId
 *     && finalBlocks.some(b => b.type === 'text' && b.text.length > 0)
 *   const visLevendeTur = streaming || afslutterSvarPacing
 *
 * `visLevendeTur` gatede BÅDE at den levende tur blev tegnet OG at
 * `udenAktivRun`-filteret var aktivt. Gik turen tilbage til værktøjsarbejde
 * efter teksten, flyttede `deriveChatFlow` blokken ud af `finalBlocks` (den
 * sidste grænse lå EFTER teksten) → `afslutterSvarPacing` blev falsk → begge
 * gates faldt bort i samme frame, og serverens persisterede række stod alene
 * tilbage oven over den halvt-pacede tekst.
 *
 * Rettelsen er at adskille de tre spørgsmål, som er tre forskellige:
 *
 *  1. `paceVindue`      — er vi i vinduet hvor svaret skal rulles færdigt?
 *  2. `afslutterSvarPacing` — har paceren en sluttekst at rulle ud?
 *  3. `filterAktiv`     — er der en levende tur PÅ SKÆRMEN med indhold, så
 *                         dens persisterede kopi skal skjules?
 *
 * Spørgsmål 3 må aldrig være bredere end 2+tegningen: en tom levende tur der
 * skjuler den persisterede række ville efterlade skærmen uden svar.
 */

export interface PacingInput {
  /** `stream.status` — 'working' mens strømmen løber. */
  status: string
  /** Runnet der strømmes lige nu. */
  activeRunId: string | null
  /** Runnet hvis sluttekst allerede er rullet færdigt. */
  pacedAnswerRunId: string | null
  /** Har `deriveChatFlow` en text-blok i `finalBlocks`? */
  harSlutblok: boolean
  /** Har serveren sendt `final_answer_start` for dette run? */
  finalAnswerStarted: boolean
  /** Normaliseret tekst af de levende blokke (kan være tom). */
  levendeTekst: string
}

export interface PacingGate {
  paceVindue: boolean
  afslutterSvarPacing: boolean
  visLevendeTur: boolean
  filterAktiv: boolean
}

export function svarPacingGate(input: PacingInput): PacingGate {
  const paceVindue = input.status === 'done'
    && !!input.activeRunId
    && input.pacedAnswerRunId !== input.activeRunId

  // PACEREN kræver en sluttekst at rulle ud. Uden den ville den «pace» et svar
  // den ikke ved hvor er.
  //
  // `finalAnswerStarted` er serverens signal om at SLUTTEKSTEN er begyndt, og
  // det overlever at et værktøj efter teksten flytter blokken ud af
  // `finalBlocks` — hvilket `harSlutblok` ikke gør. Målt 29/10-2026: uden det
  // faldt pacen bort midt i sit eget vindue.
  const afslutterSvarPacing = paceVindue && (input.harSlutblok || input.finalAnswerStarted)

  // DEN LEVENDE TUR tegnes mens strømmen løber og mens pacen indhenter den.
  const visLevendeTur = input.status === 'working' || afslutterSvarPacing

  // FILTERET følger tegningen — men kræver indhold. En tom levende tur må ikke
  // skjule den persisterede række, for så er der intet tilbage på skærmen.
  const filterAktiv = visLevendeTur && input.levendeTekst.length > 0

  return { paceVindue, afslutterSvarPacing, visLevendeTur, filterAktiv }
}
