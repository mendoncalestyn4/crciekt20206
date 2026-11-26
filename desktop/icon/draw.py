"""The program's icon (your design, approved 26 November), drawn sharp: full.svg (navy tile, faint charts, red ball, the
bat across it, CRICKET STATS PACK) for the big sizes, small.svg (the ball and bat alone) for the small ones Windows
uses. tools/make_icon.py turns them into the program's icon file."""
import base64, pathlib
OUT = pathlib.Path(__file__).parent
DEFS = '''<defs>
<linearGradient id="frame" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e9edf2"/><stop offset=".5" stop-color="#aab3bf"/><stop offset="1" stop-color="#6f7986"/></linearGradient>
<radialGradient id="navy" cx="50%" cy="40%" r="70%"><stop offset="0" stop-color="#34496b"/><stop offset=".6" stop-color="#1d2d4a"/><stop offset="1" stop-color="#111c31"/></radialGradient>
<radialGradient id="ball" cx="36%" cy="30%" r="78%"><stop offset="0" stop-color="#ff7a6e"/><stop offset=".35" stop-color="#d4282a"/><stop offset=".8" stop-color="#8b0d12"/><stop offset="1" stop-color="#5c060a"/></radialGradient>
<linearGradient id="wood" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#c9925a"/><stop offset=".35" stop-color="#f3d6a4"/><stop offset=".7" stop-color="#e2b77d"/><stop offset="1" stop-color="#a8733f"/></linearGradient>
<linearGradient id="grip" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#9c6b3a"/><stop offset=".5" stop-color="#d9a86a"/><stop offset="1" stop-color="#8a5a2e"/></linearGradient>
<linearGradient id="silver" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#dfe4ea"/><stop offset=".52" stop-color="#b9c1cb"/><stop offset="1" stop-color="#eef1f5"/></linearGradient>
<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="6" stdDeviation="7" flood-color="#000" flood-opacity=".45"/></filter>
</defs>'''

def charts():
    c = '#9fb4d3'
    s = f'<g opacity=".55" stroke="{c}" fill="none" stroke-width="2">'
    # top left: bar chart with axes
    s += '<path d="M96 96 V214 H232"/>'
    for i, h in enumerate([28, 44, 36, 70, 58, 88, 64]):
        s += f'<rect x="{106 + i*17}" y="{212 - h}" width="10" height="{h}" fill="{c}" fill-opacity=".55" stroke="none"/>'
    # bottom left: line chart
    s += '<path d="M96 236 V330 H220"/><path d="M100 318 L124 300 L146 308 L170 274 L192 286 L214 252" stroke-width="3"/>'
    s += '<path d="M100 324 L124 312 L146 318 L170 296 L192 304 L214 280" stroke-width="2" opacity=".7"/>'
    # right: bars and a rising line with dots
    s += '<path d="M300 220 V330 H420"/>'
    for i, h in enumerate([34, 58, 46, 80, 98]):
        s += f'<rect x="{310 + i*22}" y="{328 - h}" width="13" height="{h}" fill="{c}" fill-opacity=".55" stroke="none"/>'
    s += '<path d="M300 170 L330 184 L356 150 L384 162 L414 118" stroke-width="3"/>'
    for x, y in [(300, 170), (330, 184), (356, 150), (384, 162), (414, 118)]:
        s += f'<circle cx="{x}" cy="{y}" r="4" fill="{c}"/>'
    s += '<path d="M300 96 H420 M300 112 H380" stroke-dasharray="3 6"/>'
    return s + '</g>'

def ball(cx, cy, r):
    s = f'<g filter="url(#shadow)"><circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#ball)"/></g>'
    # the seam: a band across the ball, two rows of stitches
    s += (f'<path d="M{cx - r*0.78},{cy - r*0.62} C{cx - r*0.25},{cy - r*0.05} {cx + r*0.25},{cy + r*0.05} {cx + r*0.78},{cy + r*0.62}" '
          f'fill="none" stroke="#f6e7e1" stroke-width="{r*0.05:.1f}" stroke-dasharray="{r*0.07:.1f} {r*0.06:.1f}"/>'
          f'<path d="M{cx - r*0.86},{cy - r*0.46} C{cx - r*0.30},{cy + r*0.10} {cx + r*0.20},{cy + r*0.18} {cx + r*0.66},{cy + r*0.76}" '
          f'fill="none" stroke="#f6e7e1" stroke-width="{r*0.05:.1f}" stroke-dasharray="{r*0.07:.1f} {r*0.06:.1f}"/>'
          f'<path d="M{cx - r*0.82},{cy - r*0.54} C{cx - r*0.28},{cy + r*0.02} {cx + r*0.22},{cy + r*0.11} {cx + r*0.72},{cy + r*0.69}" '
          f'fill="none" stroke="#7a0a0e" stroke-width="{r*0.06:.1f}" opacity=".6"/>')
    s += f'<ellipse cx="{cx - r*0.38}" cy="{cy - r*0.45}" rx="{r*0.26}" ry="{r*0.14}" fill="#fff" opacity=".28" transform="rotate(-28 {cx - r*0.38} {cy - r*0.45})"/>'
    return s

def bat(cx, cy, scale=1.0, angle=-40):
    # drawn upright around (0,0), then turned and placed: blade at the bottom left, handle at the top right
    s = f'<g transform="translate({cx} {cy}) rotate({angle + 90}) scale({scale})" filter="url(#shadow)">'
    s += '<path d="M-26 -10 L26 -10 L24 150 Q0 166 -24 150 Z" fill="url(#wood)" stroke="#8a5a2e" stroke-width="2"/>'
    s += '<path d="M-6 -6 L-4 146" stroke="#fff" stroke-opacity=".35" stroke-width="5"/>'
    s += '<path d="M-10 -10 L10 -10 L8 -118 L-8 -118 Z" fill="url(#grip)" stroke="#6e4522" stroke-width="2"/>'
    for y in range(-110, -14, 10):
        s += f'<path d="M-9 {y} L9 {y + 6}" stroke="#6e4522" stroke-width="2" opacity=".6"/>'
    s += '<ellipse cx="0" cy="-122" rx="12" ry="7" fill="#b07a44" stroke="#6e4522" stroke-width="2"/>'
    return s + '</g>'

def full():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{DEFS}'
            '<rect x="10" y="10" width="492" height="492" rx="84" fill="url(#frame)"/>'
            '<rect x="26" y="26" width="460" height="460" rx="70" fill="url(#navy)"/>'
            + charts() + ball(250, 222, 96) + bat(258, 212, 1.32) +
            '<g font-family="DejaVu Sans, Arial Black, Arial" font-weight="900" text-anchor="middle" stroke="#0b1324" '
            'stroke-width="5" paint-order="stroke" fill="url(#silver)">'
            '<text x="256" y="400" font-size="70" letter-spacing="2">CRICKET</text>'
            '<text x="256" y="456" font-size="44" letter-spacing="2">STATS PACK</text></g></svg>')

def small():
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">{DEFS}'
            '<rect x="10" y="10" width="492" height="492" rx="96" fill="url(#frame)"/>'
            '<rect x="30" y="30" width="452" height="452" rx="80" fill="url(#navy)"/>'
            '<clipPath id="inner"><rect x="30" y="30" width="452" height="452" rx="80"/></clipPath>'
            '<g clip-path="url(#inner)">' + ball(256, 250, 150) + bat(262, 244, 1.72) + '</g></svg>')

(OUT / "full.svg").write_text(full())
(OUT / "small.svg").write_text(small())
