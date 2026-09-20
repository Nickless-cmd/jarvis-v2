# Jarvis Puls

Approved mark: three rounded bars, turquoise `#49c9b8`.
`puls.svg` is the static source. App launchers use an opaque `#0d1117`
background; favicons and tray images have transparent backgrounds.

Regenerate desktop, tray, Expo and native Android assets:

```sh
python scripts/generate_puls_icons.py
```

Requires Pillow and `rsvg-convert`. Android adaptive foregrounds keep the mark
inside the safe area. Existing raster dimensions are preserved.

Desk's `JarvisRing` compatibility component and web's `JarvisPulse` use the
same three bars. Working pulses on a four-second cycle; idle stays still.
Web/Desk respect reduced-motion preferences. Error remains a distinct red
state. Tray attention retains turquoise with a small amber badge. Its existing
`tray-rot-*` filenames are retained for compatibility, but show pulse frames.
