/** Content Security Policy for Electron renderer pages. */
export function rendererCsp({ development, connectOrigins }: {
  development: boolean
  connectOrigins: string[]
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
  return [
    "default-src 'self'",
    // Shiki's Oniguruma tokenizer compiles WebAssembly in the renderer.
    // This permits that operation without enabling JavaScript eval.
    "script-src 'self' 'wasm-unsafe-eval'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: blob:",
    "font-src 'self' data:",
    connect,
  ]
}
