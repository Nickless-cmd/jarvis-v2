/** Tids-bevidst greeting til tom-session-skærmen (spejlet fra jarvis-desk).
 *  Ren funktion: bucket bestemmes af klokkeslæt, `line` vælges deterministisk
 *  fra en pulje via `seed`, og `tint` toner presence-ringen efter tidspunktet. */

export interface Greeting {
  glyph: string
  hello: string
  line: string
  tint: string
}

type Bucket = { glyph: string; hello: string; tint: string; lines: string[] }

const MORNING: Bucket = {
  glyph: '🌅', hello: 'Godmorgen', tint: '#f6b24a',
  lines: ['Hvad skal vi i gang med?', 'Frisk start — hvor begynder vi?', 'Klar når du er.', 'Kaffe og kode?']
}
const DAY: Bucket = {
  glyph: '☀️', hello: 'God dag', tint: '#6ea8fe',
  lines: ['Hvad arbejder vi på?', 'Hvor kan jeg hjælpe?', 'Sig til — jeg lytter.', 'Lad os få noget fra hånden.']
}
const AFTERNOON: Bucket = {
  glyph: '🌆', hello: 'God eftermiddag', tint: '#e08a5b',
  lines: ['Hvad mangler vi at nå i dag?', 'Hvor er vi henne?', 'Skal vi rydde resten af listen?', 'Klar til næste skridt.']
}
const EVENING: Bucket = {
  glyph: '🌙', hello: 'Godaften', tint: '#9b8cff',
  lines: ['Hvad skal vi i gang med?', 'Rolig aften — hvad har du på sinde?', 'Jeg er her, månen er fremme.', 'Lad os tage en stille en.']
}
const NIGHT: Bucket = {
  glyph: '🌙', hello: 'Godnat', tint: '#6c6ad0',
  lines: ['Stadig vågen? Jeg holder dig med selskab.', 'Sent på den — hvad tænker du på?', 'Natteskift. Hvor begynder vi?', 'Stille timer. Sig frem.']
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
  return { glyph: b.glyph, hello: b.hello, line: b.lines[idx]!, tint: b.tint }
}
