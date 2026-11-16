"""Drawing (SVG) of the staff and fingering diagrams, and the final HTML page."""

import html

from .fingerings import fingering
from .notes import DIATONIC_INDEX

NOTE_WIDTH = 70        # horizontal space per note
MEASURE_MARGIN = 18
MAX_WIDTH = 1000       # maximum width of a system (line of music)
SPACE = 10             # distance between staff lines
STAFF_TOP = 75         # y of the top staff line (relative to the system)
STAFF_START = 60       # room for the clef
SYSTEM_HEIGHT = 345
DIAGRAM_SCALE = 1.25   # size of the fingering diagram (1 = size of the reference charts)

BLACK, WHITE, RED = "#111", "#fff", "#d62728"


def note_y(note, staff_top):
    """F5 sits on the top line; each diatonic step moves half a space."""
    f5 = 5 * 7 + DIATONIC_INDEX["F"]
    return staff_top + (f5 - note.diatonic) * SPACE / 2


def svg_note(note, x, staff_top):
    parts = []
    if note.is_rest:
        y = staff_top + 1.5 * SPACE
        parts.append(f'<rect x="{x-7}" y="{y}" width="14" height="{SPACE/2}" fill="{BLACK}"/>')
        return "".join(parts)

    y = note_y(note, staff_top)
    staff_bottom = staff_top + 4 * SPACE
    # ledger lines
    ly = staff_bottom + SPACE
    while ly <= y + 0.1:
        parts.append(f'<line x1="{x-11}" y1="{ly}" x2="{x+11}" y2="{ly}" stroke="{BLACK}" stroke-width="1.2"/>')
        ly += SPACE
    ly = staff_top - SPACE
    while ly >= y - 0.1:
        parts.append(f'<line x1="{x-11}" y1="{ly}" x2="{x+11}" y2="{ly}" stroke="{BLACK}" stroke-width="1.2"/>')
        ly -= SPACE
    # note head
    parts.append(f'<ellipse cx="{x}" cy="{y}" rx="6.2" ry="4.4" transform="rotate(-20 {x} {y})" fill="{BLACK}"/>')
    if note.alter:
        parts.append(f'<text x="{x-10}" y="{y+5}" font-size="17" text-anchor="end" '
                     f'font-family="Segoe UI Symbol, DejaVu Sans, serif">{note.accidental()}</text>')
    return "".join(parts)


def svg_fingering(closed, changed, cx, y0, *, out_of_range=False):
    """Vertical key diagram, in the style of flute fingering charts."""
    if out_of_range:
        return (f'<text x="{cx}" y="{y0+60}" font-size="11" text-anchor="middle" fill="#888">out of</text>'
                f'<text x="{cx}" y="{y0+74}" font-size="11" text-anchor="middle" fill="#888">range</text>')

    S = DIAGRAM_SCALE

    def X(dx):
        return round(cx + dx * S, 2)

    def Y(dy):
        return round(y0 + dy * S, 2)

    def style(key, stroke=1.3):
        color = RED if key in changed else BLACK
        fill = color if key in closed else WHITE
        return f'fill="{fill}" stroke="{color}" stroke-width="{stroke}" stroke-linejoin="round"'

    def hole(key, dy, title):
        return (f'<circle cx="{X(0)}" cy="{Y(dy)}" r="{4.9*S}" {style(key)}>'
                f'<title>{title}</title></circle>')

    p = []
    # Reference rows (units of the original drawing, multiplied by S)
    L = [6, 22, 38]          # left hand fingers 1-2-3
    R = [66, 82, 98]         # right hand fingers 1-2-3

    # Thumb (B key): a "comma" – round head on the left, between fingers 1 and 2,
    # with a tail going down to the level of finger 2.
    hx, hy, r = -10.6, 12.6, 3.8
    tip = L[1] + 1.2
    p.append(
        f'<path d="M {X(-6.9)} {Y(tip)} L {X(hx+r)} {Y(hy)} '
        f'A {r*S} {r*S} 0 1 0 {X(hx+0.9)} {Y(hy+3.69)} L {X(-8.4)} {Y(tip+0.2)} Z" '
        f'{style("T")}><title>Left thumb (B key)</title></path>')

    for i, key in enumerate(["L1", "L2", "L3"]):
        p.append(hole(key, L[i], f"Left hand – finger {i+1}"))

    # G♯ key: curved lever to the right of finger 3 (only shown when used).
    # Teardrop shape: round head at the top right, tapering to a thin tail
    # with a flat bottom edge, just below finger 3.
    if "Gs" in closed or "Gs" in changed:
        y3 = L[2]
        hr = 3.1 * S
        p.append(
            f'<path d="M {X(-0.2)} {Y(y3+9.6)} L {X(5.5)} {Y(y3+9.5)} '
            f'Q {X(11.5)} {Y(y3+8.5)} {X(14)} {Y(y3+2.3)} '
            f'A {hr} {hr} 0 1 0 {X(8)} {Y(y3+1)} '
            f'Q {X(8)} {Y(y3+6.5)} {X(2.5)} {Y(y3+7.4)} '
            f'L {X(-0.2)} {Y(y3+7.6)} Z" {style("Gs", 1)}>'
            f'<title>G♯ key (left pinky)</title></path>')

    # divider between the hands
    p.append(f'<line x1="{X(-6)}" y1="{Y(52)}" x2="{X(6)}" y2="{Y(52)}" stroke="#444" stroke-width="{1.3*S}"/>')

    for i, key in enumerate(["R1", "R2", "R3"]):
        p.append(hole(key, R[i], f"Right hand – finger {i+1}"))

    # E♭ key: "shoe" – flat base, tall rounded end on the left, sloping down to the right
    b = R[2] + 16  # base
    p.append(
        f'<path d="M {X(-7.2)} {Y(b)} L {X(5.6)} {Y(b)} '
        f'Q {X(6.6)} {Y(b-2.4)} {X(3.2)} {Y(b-2.9)} '
        f'Q {X(0.4)} {Y(b-3.3)} {X(-1.6)} {Y(b-5.6)} '
        f'Q {X(-3.6)} {Y(b-7.5)} {X(-6.2)} {Y(b-6.5)} '
        f'Q {X(-8.2)} {Y(b-5)} {X(-7.2)} {Y(b)} Z" {style("Eb")}>'
        f'<title>E♭ key (right pinky)</title></path>')

    # Foot keys (only shown for the low notes that use them):
    # half-disc = C♯, bars = C and B rollers, gizmo
    if any(k in closed or k in changed for k in ("Cs", "C", "B")):
        t = b + 2.5
        p.append(f'<path d="M {X(-3)} {Y(t)} A {4.2*S} {4.2*S} 0 0 0 {X(-3)} {Y(t+8.4)} Z" '
                 f'{style("Cs", 1)}><title>C♯ key (foot)</title></path>')
        for i, (key, name) in enumerate([("C", "C key"), ("B", "B key"), ("Gz", "Gizmo key (high C)")]):
            p.append(f'<rect x="{X(-1.4 + i*3.3)}" y="{Y(t)}" width="{2*S}" height="{8.4*S}" '
                     f'{style(key, 1)}><title>{name} (foot, roller)</title></rect>')
    return "".join(p)


def layout_systems(measures):
    """Split the measures into systems (lines) that fit the maximum width."""
    systems, current, width = [], [], STAFF_START
    for m in measures:
        w = len(m) * NOTE_WIDTH + MEASURE_MARGIN
        if current and width + w > MAX_WIDTH:
            systems.append(current)
            current, width = [], STAFF_START
        current.append(m)
        width += w
    if current:
        systems.append(current)
    return systems


def render_svg(measures):
    """Return (svg, set of out-of-range note names)."""
    systems = layout_systems(measures)
    width = max(STAFF_START + sum(len(m) * NOTE_WIDTH + MEASURE_MARGIN for m in s) for s in systems) + 10
    height = len(systems) * SYSTEM_HEIGHT
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" class="score" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="Segoe UI, Arial, sans-serif">']

    previous = None
    out_of_range = set()
    for si, system in enumerate(systems):
        staff_top = si * SYSTEM_HEIGHT + STAFF_TOP
        end = STAFF_START + sum(len(m) * NOTE_WIDTH + MEASURE_MARGIN for m in system)
        for i in range(5):
            y = staff_top + i * SPACE
            out.append(f'<line x1="5" y1="{y}" x2="{end}" y2="{y}" stroke="{BLACK}" stroke-width="1"/>')
        out.append(f'<text x="8" y="{staff_top + 3.3*SPACE}" font-size="{6.2*SPACE}" '
                   f'font-family="Segoe UI Symbol, Noto Music, DejaVu Sans, serif">𝄞</text>')
        out.append(f'<line x1="5" y1="{staff_top}" x2="5" y2="{staff_top+4*SPACE}" stroke="{BLACK}" stroke-width="1"/>')

        x = STAFF_START
        for measure in system:
            for ni, note in enumerate(measure):
                cx = x + ni * NOTE_WIDTH + NOTE_WIDTH / 2
                out.append(svg_note(note, cx, staff_top))
                label_y = staff_top + 7.5 * SPACE
                if note.is_rest:
                    out.append(f'<text x="{cx}" y="{label_y}" font-size="12" text-anchor="middle" fill="#888">rest</text>')
                    continue
                out.append(f'<text x="{cx}" y="{label_y}" font-size="13" text-anchor="middle">'
                           f'{html.escape(note.name())}</text>')
                closed = fingering(note)
                diagram_y = label_y + 16
                if closed is None:
                    out_of_range.add(note.name())
                    out.append(svg_fingering(set(), set(), cx, diagram_y, out_of_range=True))
                    previous = None
                    continue
                changed = set() if previous is None else (closed ^ previous)
                out.append(svg_fingering(closed, changed, cx, diagram_y))
                previous = closed
            x += len(measure) * NOTE_WIDTH + MEASURE_MARGIN
            barline = x - MEASURE_MARGIN / 2
            out.append(f'<line x1="{barline}" y1="{staff_top}" x2="{barline}" y2="{staff_top+4*SPACE}" '
                       f'stroke="{BLACK}" stroke-width="1"/>')
    out.append("</svg>")
    return "".join(out), out_of_range


LEGEND = f"""
<svg xmlns="http://www.w3.org/2000/svg" class="score" width="790" height="175" viewBox="0 0 790 175" font-family="Segoe UI, Arial, sans-serif" font-size="11.5">
  {svg_fingering(frozenset(["T","L1","L2","L3","Gs","R3","Eb","Cs"]), set(), 100, 8)}
  <g fill="#333">
    <text x="72" y="29" text-anchor="end">thumb →</text>
    <text x="126" y="19.5">← left hand finger 1 (index)</text>
    <text x="126" y="39.5">← finger 2 (middle)</text>
    <text x="126" y="59.5">← finger 3 (ring)</text>
    <text x="126" y="76">  ↳ curved lever = G♯ key (left pinky), shown only when used</text>
    <text x="126" y="94.5">← right hand finger 1</text>
    <text x="126" y="114.5">← finger 2</text>
    <text x="126" y="134.5">← finger 3</text>
    <text x="126" y="152">← “shoe” = E♭ key (right pinky)</text>
    <text x="126" y="168">← foot keys: half-disc = C♯, bars = C / B (low notes only)</text>
  </g>
  <g fill="#333" font-size="12">
    <text x="590" y="100">● black = press / cover</text>
    <text x="590" y="118">○ white = leave open</text>
    <text x="590" y="136" fill="{RED}">● red = changed from</text>
    <text x="590" y="152" fill="{RED}">   the previous note</text>
  </g>
</svg>"""


def render_html(title, measures):
    """Full HTML page with the legend and the annotated score."""
    svg, out_of_range = render_svg(measures)
    warning = ""
    if out_of_range:
        warning = ("<p class='warning'>Notes outside this chart's range (B3 to A6): "
                   + ", ".join(sorted(out_of_range)) + ".</p>")
    safe_title = html.escape(title or "Fingering")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{safe_title} – flute fingering</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #111; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #666; margin: 0 0 16px; }}
  details {{ margin-bottom: 18px; }}
  .warning {{ color: #a33; }}
  svg.score {{ max-width: 100%; height: auto; }}
  @media print {{ details {{ display: none; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
<h1>{safe_title}</h1>
<p class="sub">Concert flute – standard fingerings (Boehm system)</p>
<details open><summary>How to read the diagram</summary>{LEGEND}</details>
{warning}
{svg}
</body>
</html>"""
