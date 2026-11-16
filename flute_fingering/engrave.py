"""Full music notation with Verovio, with a fingering diagram under every note.

How it works:

1. Each playable note gets its name (e.g. "F♯4") as a lyric. Verovio already knows
   how to lay out lyrics: it spreads the notes so the words don't collide and
   leaves room under the staff. That gives the diagrams enough horizontal space.
2. Verovio (https://www.verovio.org) engraves the MusicXML into SVG.
3. The real pitch of each note is read from Verovio's MEI export (which resolves
   key signatures), and its position from the SVG.
4. Each system (line of music) is moved down to make room, and a fingering
   diagram is drawn under every note name.
"""

import re
import xml.etree.ElementTree as ET

import verovio

from .diagram import svg_fingering
from .errors import FingeringError
from .fingerings import fingering
from .notes import ACCIDENTAL_SYMBOL, Note

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ET.register_namespace("", SVG_NS)

VEROVIO_OPTIONS = {
    "pageWidth": 2000,          # with scale 50 -> 1000 px wide
    "pageHeight": 60000,        # tall page: everything on one page
    "scale": 50,
    "adjustPageHeight": True,
    "breaks": "auto",
    "header": "none",           # the title is shown by the HTML page
    "footer": "none",
    "svgRemoveXlink": True,
    "xmlIdSeed": 1,             # deterministic ids
}

LABEL_PADDING = " "  # non-breaking space around the note name: widens the room for each diagram
DIAGRAM_HEIGHT = 165      # height of a fingering diagram, in diagram units
DIAGRAM_PER_SPACE = 10   # diagram units per staff space (bigger = smaller diagram)

_ACCID = {"s": 1, "f": -1, "ss": 2, "x": 2, "ff": -2, "n": 0}
_TRANSLATE = re.compile(r"translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)")
_PATH_LINE = re.compile(r"M\s*([-\d.]+)\s+([-\d.]+)\s*L\s*([-\d.]+)\s+([-\d.]+)")

try:  # Verovio prints harmless warnings (e.g. about MIDI timing) to the console
    verovio.enableLog(verovio.LOG_OFF)
except AttributeError:
    pass


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _classes(el):
    return (el.get("class") or "").split()


def _children(el, name):
    return [c for c in el if _local(c.tag) == name]


# ---------------------------------------------------------------------------
# 1. Note names as lyrics
# ---------------------------------------------------------------------------
def add_note_name_lyrics(musicxml):
    """Replace the lyrics of the first part with the note names, one per playable note.

    Rests, grace notes, lower notes of chords and tied continuations get no name
    (and therefore no diagram).
    """
    root = ET.fromstring(musicxml)
    part = next(c for c in root if _local(c.tag) == "part")
    for note in part.iter():
        if _local(note.tag) != "note":
            continue
        for old in _children(note, "lyric"):
            note.remove(old)
        pitch = next(iter(_children(note, "pitch")), None)
        ties = {t.get("type") for t in _children(note, "tie")}
        if (pitch is None or _children(note, "chord") or _children(note, "grace")
                or ("stop" in ties and "start" not in ties)):
            continue
        step = _children(pitch, "step")[0].text.strip()
        octave = _children(pitch, "octave")[0].text.strip()
        alter_el = _children(pitch, "alter")
        alter = int(round(float(alter_el[0].text))) if alter_el else 0
        name = f"{step}{ACCIDENTAL_SYMBOL.get(alter, '')}{octave}"

        lyric = ET.Element("lyric", {"number": "1"})
        ET.SubElement(lyric, "syllabic").text = "single"
        ET.SubElement(lyric, "text").text = LABEL_PADDING + name + LABEL_PADDING
        # <lyric> comes before <play>/<listen> in the MusicXML schema
        tail = next((i for i, c in enumerate(note) if _local(c.tag) in ("play", "listen")), len(note))
        note.insert(tail, lyric)
    return ET.tostring(root, encoding="unicode")


# ---------------------------------------------------------------------------
# 2-3. Engraving, pitches and positions
# ---------------------------------------------------------------------------
def _render(musicxml):
    tk = verovio.toolkit()
    tk.setOptions(VEROVIO_OPTIONS)
    if not tk.loadData(musicxml):
        raise FingeringError("Verovio could not read this score.")
    pages = [tk.renderToSVG(p) for p in range(1, tk.getPageCount() + 1)]
    return pages, tk.getMEI()


def _pitches_from_mei(mei):
    """{note id: Note} with the sounding pitch (key signature included)."""
    notes = {}
    for el in ET.fromstring(mei).iter():
        if _local(el.tag) == "note" and el.get("pname") and el.get("oct"):
            accid = el.get("accid") or el.get("accid.ges")
            for child in _children(el, "accid"):
                accid = child.get("accid") or child.get("accid.ges") or accid
            notes[el.get(XML_ID)] = Note(el.get("pname").upper(), _ACCID.get(accid, 0), int(el.get("oct")))
    return notes


def _staff_lines(staff):
    ys = []
    for path in _children(staff, "path"):
        m = _PATH_LINE.match(path.get("d", ""))
        if m and m.group(2) == m.group(4):
            ys.append(float(m.group(2)))
    return sorted(ys)


# Notehead widths in staff spaces (SMuFL glyphs used by Verovio); anything else counts as black
_NOTEHEAD_WIDTH = {"E0A0": 2.5, "E0A2": 1.69}  # double whole, whole
_BLACK_NOTEHEAD = 1.18


def _notehead_center(note, space):
    """x of the center of the note head (Verovio places glyphs by their left edge)."""
    head = next((h for h in note if "notehead" in _classes(h)), None)
    use = next((u for u in head.iter() if _local(u.tag) == "use"), None) if head is not None else None
    if use is None:
        return None
    m = _TRANSLATE.search(use.get("transform", ""))
    if not m:
        return None
    glyph = (use.get("href") or use.get(f"{{{XLINK_NS}}}href") or "").lstrip("#")[:4]
    return float(m.group(1)) + _NOTEHEAD_WIDTH.get(glyph, _BLACK_NOTEHEAD) * space / 2


def _labeled_notes(system, space):
    """Yield (note id, x of the note head center, y of the note name) for every note with a name.

    The note name is re-centered on the note head: Verovio anchors lyrics by their left
    edge, using its own font metrics, which may not match the browser's font.
    """
    for note in system.iter():
        if "note" not in _classes(note):
            continue
        verse = next((v for v in note.iter() if "verse" in _classes(v)), None)
        if verse is None:
            continue
        text = next((t for t in verse.iter() if _local(t.tag) == "text"), None)
        center = _notehead_center(note, space)
        if text is None or center is None or not text.get("y"):
            continue
        text.set("x", f"{center:.0f}")
        text.set("text-anchor", "middle")
        yield note.get("id"), center, float(text.get("y"))


def _first_staff_lines(system):
    for el in system.iter():
        if "staff" in _classes(el):
            lines = _staff_lines(el)
            if len(lines) >= 5:
                return lines
    return None


# ---------------------------------------------------------------------------
# 4. Diagrams
# ---------------------------------------------------------------------------
def engrave(musicxml):
    """Engrave the score and add the fingering diagrams.

    Returns (list of SVG strings, one per page; set of out-of-range note names).
    """
    pages, mei = _render(add_note_name_lyrics(musicxml))
    pitches = _pitches_from_mei(mei)
    state = {"previous": None, "out_of_range": set()}
    return [_add_fingerings(svg, pitches, state) for svg in pages], state["out_of_range"]


def _add_fingerings(svg, pitches, state):
    root = ET.fromstring(svg)
    parents = {child: parent for parent in root.iter() for child in parent}

    # Part names ("Voice", "Flute"...) are not needed
    for el in list(root.iter()):
        if {"label", "labelAbbr"} & set(_classes(el)):
            parents[el].remove(el)

    inner = next(el for el in root.iter() if "definition-scale" in _classes(el))
    vb = [float(v) for v in inner.get("viewBox").split()]

    offset = 0.0
    for system in [el for el in root.iter() if "system" in _classes(el)]:
        lines = _first_staff_lines(system)
        space = (lines[-1] - lines[0]) / 4 if lines else 0
        labeled = list(_labeled_notes(system, space)) if lines else []
        if not labeled:
            if offset:
                system.set("transform", f"translate(0,{offset:.0f})")
            continue
        k = space / DIAGRAM_PER_SPACE
        label_y = max(y for _, _, y in labeled)
        diagram_y = label_y + 0.9 * space

        markup = []
        for note_id, x, _ in labeled:
            note = pitches.get(note_id)
            if note is None:
                continue
            closed = fingering(note)
            if closed is None:
                state["out_of_range"].add(note.name())
                state["previous"] = None
                diagram = svg_fingering(set(), set(), 0, 0, out_of_range=True)
            else:
                previous = state["previous"]
                changed = set() if previous is None else (closed ^ previous)
                diagram = svg_fingering(closed, changed, 0, 0)
                state["previous"] = closed
            markup.append(f'<g transform="translate({x:.0f},{diagram_y:.0f}) scale({k:.3f})">{diagram}</g>')

        group = ET.SubElement(system, f"{{{SVG_NS}}}g", {"class": "fingerings"})
        group.extend(ET.fromstring(f'<g xmlns="{SVG_NS}">{"".join(markup)}</g>'))
        if offset:
            system.set("transform", f"translate(0,{offset:.0f})")
        offset += (diagram_y - label_y) + DIAGRAM_HEIGHT * k + 1.0 * space

    # Grow the page to fit the added space, and make it scalable
    vb[3] += offset
    inner.set("viewBox", " ".join(f"{v:g}" for v in vb))
    width_px = float(root.get("width", "0").rstrip("px") or 0) or vb[2] / 10
    height_px = vb[3] * width_px / vb[2]
    root.set("width", f"{width_px:g}")
    root.set("height", f"{height_px:.0f}")
    root.set("viewBox", f"0 0 {width_px:g} {height_px:.0f}")
    root.set("class", "score")
    return ET.tostring(root, encoding="unicode")
