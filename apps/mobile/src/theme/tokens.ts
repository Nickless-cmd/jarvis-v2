/**
 * Design-tokens — ChatGPT-paritet (dark).
 *
 * MÅLT pixel for pixel i Bjørns referenceskærmbilleder (R1, R2, R8) 2026-09-02,
 * ikke afskrevet fra spec-teksten. Tre steder afveg speccens beskrivelse fra
 * det faktiske billede, og målingen vandt:
 *
 *   1. Det AKTIVE segment er MØRKERE (#222222) end beholderen (#414141).
 *      Speccen sagde «aktivt tab: lysere grå pille».
 *   2. Voice-knappen er ENSFARVET (ikke en gradient). Referencens lilla var
 *      #A07FEB; vi bruger bevidst en anden kulør — se Accent nedenfor.
 *   3. Den lilla boble er BRUGERENS besked. AI-svaret står som ren tekst uden
 *      boble. Speccen tilskrev boblen AI-hilsenen.
 *
 * Værdierne er efterprøvet igen 2026-09-02 i TABSFRIE png-skærmbilleder taget
 * direkte fra ChatGPT-appen på enheden. JPEG-referencerne var komprimerede og
 * gav #9D84DB hvor den sande accent er #A07FEB. Måler man farver, skal kilden
 * være tabsfri — ellers måler man kompressionen.
 *
 * Nøglenavnene er bevaret fra V1, så de ~30 komponenter der bruger dem skifter
 * med. Kun værdierne er nye. Planen foreslog at omdøbe nøglerne for at fremtvinge
 * en gennemgang via typefejl; det er fravalgt her, fordi det ville have spredt
 * en stor visuel ændring ud over hver eneste fil samtidig med at Arbejde-rummet
 * skulle E2E-testes. Den gennemgang hører til sit eget skridt.
 */
export const tokens = {
  color: {
    // ── Flader (målt) ───────────────────────────────────────────────
    bg0: '#000000',      // siden — ægte sort, ikke næsten-sort
    bg1: '#121212',      // diskret hævet (lister)
    bg2: '#212121',      // kort, cirkel-knapper, kontekst-pille
    bg3: '#303030',      // kodeblok, indre hævet flade
    line: '#2A2A2A',

    // ── Tekst ───────────────────────────────────────────────────────
    fg1: '#FFFFFF',
    fg2: '#B0B0B0',      // sekundær: tidsstempler, undertekst
    fg3: '#7A7A7A',      // tertiær

    // ── Accent (BEVIDST AFVIGELSE fra referencen) ───────────────────
    // Alt andet i paletten er målt i ChatGPT-appen. Accenten er ikke.
    //
    // Vi kørte en periode med referencens lilla #A07FEB, og den var korrekt
    // målt — men 1:1 på FORM behøver ikke betyde 1:1 på IDENTITET. Bjørn bad
    // om en anden farve end lilla, og valget faldt på teal: det er tættere på
    // Jarvis' oprindelige grønne (#6ee7a8) uden at være mint, og det læser
    // som instrument frem for chat-klon.
    //
    // Layout, mål og flader følger stadig referencen. Kun farven er hans.
    accent: '#3FC7B4',
    userBubble: '#10403A',   // brugerens boble — samme kulør, dybt nedtonet
    codeBg: '#303030',

    // ── Segmented control (målt — bemærk retningen) ─────────────────
    segmentTrack: '#414141',
    segmentActive: '#212121',

    // ── Status ──────────────────────────────────────────────────────
    ok: '#4CAF50',       // online-prik / kørende
    error: '#ff8080',
    warn: '#FFB347',

    // ── Dybde-lag (§3 design-sprog) ─────────────────────────────────
    depth0: '#000000',
    depth1: '#121212',
    depth2: '#1D1D1D',
    depth3: '#212121',
    accentDim: 'rgba(63, 199, 180, 0.55)',
    accentGhost: 'rgba(63, 199, 180, 0.12)',
    glassFill: 'rgba(255, 255, 255, 0.07)',
    glassLine: 'rgba(255, 255, 255, 0.10)'
  },
  radius: {
    sm: 6,
    md: 10,
    lg: 16,
    xl: 20,
    pill: 999
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24
  },
  // Animations-sandhed (ms). breath = liveness-åndedræt, heartbeat = notif-prik.
  motion: {
    durFast: 160,
    durBase: 250,
    breath: 3000,
    heartbeat: 1400
  }
} as const
