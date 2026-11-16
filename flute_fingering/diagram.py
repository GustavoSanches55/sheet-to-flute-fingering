"""Fingering diagram drawing (one vertical key diagram per note) and its legend."""

DIAGRAM_SCALE = 1.25   # size of the diagram (1 = size of the reference charts)

BLACK, WHITE, RED = "#111", "#fff", "#d62728"


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
