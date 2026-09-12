/** Hvor bredt lyset er, målt i tegn. Smallere = hårdere kant. */
export const BREDDE = 6

/**
 * Ét tegns lysstyrke-kurve, som input/output til en Animated-interpolation.
 *
 * ## Hvad det er
 *
 * Lyset er ikke en overlejring der glider hen over teksten — det er tekstens
 * EGEN lysstyrke, høj dér hvor lyset er lige nu. Én animation kører 0→1, og
 * hvert tegn oversætter den samme værdi gennem sin egen kurve, forskudt efter
 * sin plads. Resultatet er en lysende bølge der vandrer gennem ordene.
 *
 * ## Hvorfor ikke en gradient-overlejring
 *
 * Fordi der ikke er nogen. Hverken `expo-linear-gradient` eller
 * `@react-native-masked-view` er installeret, og at trække en afhængighed ind
 * for én animation er dyrere end den er værd. Denne løsning bruger kun
 * `Animated`, virker på native driver (kun opacity), og falder rent tilbage
 * til en almindelig tekst når bevægelse er slået fra.
 *
 * ## Hvorfor rejsen er længere end teksten
 *
 * Lyset skal kunne komme HELT ind fra venstre og HELT ud til højre. Gik den
 * kun fra 0 til 1, ville første og sidste tegn blinke i stedet for at blive
 * strøget.
 */
export function lysKurve(
  indeks: number, antal: number, bredde = BREDDE,
): { input: number[]; output: number[] } {
  const n = Math.max(1, antal)
  const rejse = n + bredde * 2
  // Tegnets midte på rejsen, normaliseret til 0..1.
  const midte = (indeks + bredde) / rejse
  const halv = bredde / 2 / rejse
  const punkter = [
    Math.max(0, midte - halv * 2),
    midte,
    Math.min(1, midte + halv * 2),
  ]
  // STIGENDE og UNIKKE punkter. Animated.interpolate kaster på et
  // input-array der ikke stiger — og ved korte tekster falder to punkter
  // sammen, fordi halv bliver meget lille.
  const input = [0, ...punkter, 1].filter((v, i, a) => i === 0 || v > a[i - 1]!)
  const output = input.map((v) => (v === midte ? 1 : 0.45))
  return { input, output }
}
