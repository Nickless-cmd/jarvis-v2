"""Render Jarvis Puls assets. Requires rsvg-convert and Pillow; run from any cwd.

Canonical silhouette/color: assets/brand/puls.svg. Keep the same three bars in
web/native components. Launcher backgrounds are opaque; tray/foreground aren't.
"""
from pathlib import Path
import io
import math
import subprocess
import xml.etree.ElementTree as ET
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets/brand/puls.svg'
COLOR = ET.parse(SOURCE).getroot().attrib['fill']
BG = '#0d1117'


#: Hjørneradius på app-ikonets baggrund, i viewBox-enheder (0-100).
#: 22 er skrivebordets konvention — macOS' squircle ligger på 22,4 %, og
#: GNOME/KDE tegner selv runde hjørner på alt andet end app-ikoner. Bjørn
#: 20/9-2026: «selv desktop ikonet mangler runde hjørner». `rounded=True`
#: (rx=50) er Androids RUNDE launcher og er noget andet end det her.
APP_RADIUS = 22


def svg(*, background=False, scale=1.0, phase=None, attention=False, rounded=False,
        radius=None):
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    bars = root.findall('{http://www.w3.org/2000/svg}rect')
    shapes = []
    for i, bar in enumerate(bars):
        h = float(bar.attrib['height'])
        if phase is not None:
            h *= 1 - .28 * math.cos(phase + i * .85)
        shapes.append(f'<rect x="{bar.attrib["x"]}" y="{(100-h)/2}" width="19" height="{h}" rx="9.5"/>')
    rx = 50 if rounded else (APP_RADIUS if radius is None else radius)
    backdrop = f'<rect width="100" height="100" rx="{rx}" fill="{BG}"/>' if background else ''
    badge = '<circle cx="87" cy="16" r="8" fill="#e9b567"/>' if attention else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">{backdrop}<g fill="{COLOR}" transform="translate({50*(1-scale)} {50*(1-scale)}) scale({scale})">{"".join(shapes)}</g>{badge}</svg>'


def render(dest, size, source):
    dest = ROOT / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    png = subprocess.run(['rsvg-convert', '-w', str(size), '-h', str(size)], input=source.encode(), stdout=subprocess.PIPE, check=True).stdout
    image = Image.open(io.BytesIO(png))
    if dest.suffix == '.webp':
        image.save(dest, lossless=True)
    else:
        image.save(dest)


def main():
    for app in ['ui', 'jarvis-desk']:
        dest = ROOT / f'apps/{app}/public/favicon.svg'
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(SOURCE.read_text())
    desk = 'apps/jarvis-desk/assets'
    (ROOT / desk / 'icon.svg').write_text(svg(background=True))
    for size in [16, 48, 128, 256, 512]:
        render(f'{desk}/icon-{size}.png', size, svg(background=True))
    render(f'{desk}/icon.png', 512, svg(background=True))
    for name in ['idle', 'bright', 'attention']:
        source = svg(attention=name == 'attention')
        (ROOT / desk / f'tray-{name}.svg').write_text(source)
        render(f'{desk}/tray-{name}.png', 44, source)
    # Keep existing frame filenames; their content now pulses, never rotates.
    for frame in range(40):
        render(f'{desk}/tray-rot-{frame:02}.png', 44, svg(phase=2*math.pi*frame/40))
    mobile = 'apps/mobile/assets'
    render(f'{mobile}/icon.png', 1024, svg(background=True, radius=APP_RADIUS))
    render(f'{mobile}/adaptive-icon.png', 1024, svg(scale=.65))
    render(f'{mobile}/splash-icon.png', 1024, svg(scale=.65))
    res = ROOT / 'apps/mobile/android/app/src/main/res'
    for path in res.glob('mipmap-*/ic_launcher*.webp'):
        size = Image.open(path).width
        foreground = 'foreground' in path.name
        # Android maskerer SELV: en radius her ville klippe hjørnerne to gange.
        source = svg(background=not foreground, scale=.65 if foreground else 1,
                     rounded='round' in path.name, radius=0)
        render(path, size, source)
    for path in res.glob('drawable-*/splashscreen_logo.png'):
        render(path, Image.open(path).width, svg(scale=.65))
    print('Rendered Puls favicon, desktop, tray, Expo and native Android assets.')


if __name__ == '__main__':
    main()
