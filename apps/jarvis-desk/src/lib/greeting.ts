/** Tids-bevidst greeting til tom-session-skærmen.
 *
 *  Ren funktion (testbar): bucket bestemmes af klokkeslæt, og `line` vælges
 *  deterministisk fra en pulje via `seed`. Tidspunktet står allerede i ord,
 *  så særskilte sol/måne-ikoner og tint ville blot gentage hilsenen. */

export interface Greeting {
  hello: string
  line: string
}

type Bucket = {
  hello: string
  lines: string[]
}

const MORNING: Bucket = {
  hello: 'Godmorgen',
  lines: [
    'Hvad skal vi i gang med?',
    'Frisk start — hvor begynder vi?',
    'Klar når du er.',
    'Kaffe og kode?',
  ],
}
const DAY: Bucket = {
  hello: 'God dag',
  lines: [
    'Hvad arbejder vi på?',
    'Hvor kan jeg hjælpe?',
    'Sig til — jeg lytter.',
    'Lad os få noget fra hånden.',
  ],
}
const AFTERNOON: Bucket = {
  hello: 'God eftermiddag',
  lines: [
    'Hvad mangler vi at nå i dag?',
    'Hvor er vi henne?',
    'Skal vi rydde resten af listen?',
    'Klar til næste skridt.',
  ],
}
const EVENING: Bucket = {
  hello: 'Godaften',
  lines: [
    'Hvad skal vi i gang med?',
    'Rolig aften — hvad har du på sinde?',
    'Jeg er her, månen er fremme.',
    'Lad os tage en stille en.',
  ],
}
const NIGHT: Bucket = {
  hello: 'Godnat',
  lines: [
    'Stadig vågen? Jeg holder dig med selskab.',
    'Sent på den — hvad tænker du på?',
    'Natteskift. Hvor begynder vi?',
    'Stille timer. Sig frem.',
  ],
}

function bucketFor(hour: number): Bucket {
  if (hour >= 5 && hour < 10) return MORNING
  if (hour >= 10 && hour < 14) return DAY
  if (hour >= 14 && hour < 18) return AFTERNOON
  if (hour >= 18 && hour < 23) return EVENING
  return NIGHT
}

export function greetingFor(now: Date, seed: number): Greeting {
  const b = bucketFor(now.getHours())
  const idx = ((Math.floor(seed) % b.lines.length) + b.lines.length) % b.lines.length
  return { hello: b.hello, line: b.lines[idx]! }
}
