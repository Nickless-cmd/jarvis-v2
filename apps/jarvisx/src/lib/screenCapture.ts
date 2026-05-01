/**
 * Screen capture flow:
 *   1. listScreenSources() (via Electron IPC) returns thumbnails + ids
 *      for every connected screen + open window
 *   2. UI shows a picker modal
 *   3. User picks → captureSource(sourceId) calls getUserMedia with the
 *      Electron-specific desktopCapturer constraint to grab a single
 *      frame as a Blob
 *   4. Blob uploaded to /attachments/upload — same path as drag-drop
 *      attachments — so it shows up next to other images in the chat
 */

export interface ScreenSource {
  id: string
  name: string
  display_id: string
  thumbnail: string
}

export async function listSources(): Promise<ScreenSource[]> {
  if (!window.jarvisx) return []
  const result = await window.jarvisx.listScreenSources()
  if (Array.isArray(result)) return result
  return []
}

/**
 * Grabs a single frame from the picked screen/window source.
 * Returns a Blob (PNG) the caller can upload as an attachment.
 */
export async function captureSourceAsBlob(sourceId: string): Promise<Blob> {
  // Electron-specific media constraint: the chromeMediaSource must be
  // 'desktop' and chromeMediaSourceId is the source id from desktopCapturer.
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      // @ts-expect-error — Electron-only constraint, not in standard typings
      mandatory: {
        chromeMediaSource: 'desktop',
        chromeMediaSourceId: sourceId,
        maxWidth: 2560,
        maxHeight: 1440,
      },
    },
  })

  // Wait for one frame, then snap it to a canvas as PNG
  const track = stream.getVideoTracks()[0]
  if (!track) throw new Error('no video track from desktopCapturer')

  // Some platforms need a moment after track start to have valid frames
  await new Promise((resolve) => setTimeout(resolve, 250))

  const video = document.createElement('video')
  video.srcObject = stream
  video.muted = true
  await video.play()

  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas 2d context unavailable')
  ctx.drawImage(video, 0, 0)

  // Always stop the track immediately — single-frame capture
  track.stop()
  stream.getTracks().forEach((t) => t.stop())
  video.srcObject = null

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('canvas.toBlob returned null'))
          return
        }
        resolve(blob)
      },
      'image/png',
    )
  })
}
