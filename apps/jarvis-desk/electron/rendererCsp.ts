/** Content Security Policy for Electron renderer pages. */
export function rendererCsp({ development, connectOrigins, widgetNonce }: {
  development: boolean
  connectOrigins: string[]
  /** Engangs-nonce for widget-dokumentets inline-scripts.
   *
   *  Prod-grenen har ikke `'unsafe-inline'` — den ville åbne hele rendereren.
   *  Men en `srcdoc`-iframe ARVER forælderens policy, så uden en nonce blev
   *  widget'ens egne scripts blokeret i den pakkede app, mens de kørte fint på
   *  web-fladen, hvor ingen forælder-policy findes. Målt 15/10-2026: proben i
   *  widget'ens script kørte slet ikke under prod-CSP'en, og rammen blev
   *  stående på 160 px.
   *
   *  Udelades noncen (web, mobil, dev, test), står direktivet uændret. Den
   *  bruges ALDRIG i dev-grenen: dér er `'unsafe-inline'` stadig aktiv, og en
   *  nonce i samme direktiv ville ophæve den — og dermed dræbe Vite og
   *  Reacts egne inline-scripts. */
  widgetNonce?: string
}): string[] {
  const connect = `connect-src 'self' ${connectOrigins.join(' ')}`
  if (development) return [
    "default-src 'self' http://localhost:5174 ws://localhost:5174",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:5174",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    `${connect} http://localhost:5174 ws://localhost:5174`,
  ]
  // Rækkefølgen er ikke kosmetisk: `'nonce-…'` er en kilde som de andre, og en
  // tom værdi ville være en syntaksfejl der dropper HELE direktivet — derfor
  // tilføjes den kun når den findes.
  const scriptSrc = [
    "'self'",
    // Shiki's Oniguruma tokenizer compiles WebAssembly in the renderer.
    // This permits that operation without enabling JavaScript eval.
    "'wasm-unsafe-eval'",
    ...(widgetNonce ? [`'nonce-${widgetNonce}'`] : []),
  ]
  return [
    "default-src 'self'",
    `script-src ${scriptSrc.join(' ')}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    connect,
  ]
}
