"""Score reading: MusicXML (.musicxml/.xml/.mxl), plain text (.txt) and PDF/image."""

import copy
import html
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .errors import FingeringError
from .notes import Note

MUSICXML_EXTENSIONS = (".musicxml", ".xml", ".mxl")
OMR_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


@dataclass
class Score:
    """A score ready to be rendered."""
    title: str
    measures: list = field(default_factory=list)  # lists of Note (used for counting/inspection)
    musicxml: str = ""                            # first part only, as MusicXML text (drawn by Verovio)

    @property
    def note_count(self):
        return sum(1 for m in self.measures for n in m if not n.is_rest)


# ---------------------------------------------------------------------------
# MusicXML
# ---------------------------------------------------------------------------
def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _read_xml_bytes(path):
    if path.suffix.lower() != ".mxl":
        return path.read_bytes()
    with zipfile.ZipFile(path) as z:
        target = None
        if "META-INF/container.xml" in z.namelist():
            container = ET.fromstring(z.read("META-INF/container.xml"))
            for el in container.iter():
                if _local(el.tag) == "rootfile" and el.get("full-path"):
                    target = el.get("full-path")
                    break
        if target is None:
            target = next((n for n in z.namelist()
                           if n.lower().endswith((".xml", ".musicxml")) and not n.startswith("META-INF")), None)
        if target is None:
            raise FingeringError(f"No score found inside {path.name}.")
        return z.read(target)


def _load_musicxml(path):
    """Parse a MusicXML file (plain or compressed) and return its root element."""
    path = Path(path)
    try:
        root = ET.fromstring(_read_xml_bytes(path))
    except (ET.ParseError, zipfile.BadZipFile) as e:
        raise FingeringError(f"Could not read the MusicXML file {path.name}: {e}") from e
    if _local(root.tag) != "score-partwise":
        raise FingeringError("Only 'score-partwise' MusicXML is supported "
                             "(the default for MuseScore, Finale, Sibelius...).")
    if _child(root, "part") is None:
        raise FingeringError("No <part> found in the file.")
    return root


def _first_part_only(root):
    """Copy of the score keeping only the first part (the flute line), as MusicXML text."""
    root = copy.deepcopy(root)
    parts = [c for c in root if _local(c.tag) == "part"]
    keep = parts[0].get("id")
    for p in parts[1:]:
        root.remove(p)
    part_list = _child(root, "part-list")
    if part_list is not None:
        for sp in list(part_list):
            if _local(sp.tag) == "score-part" and sp.get("id") != keep:
                part_list.remove(sp)
    return root


def read_musicxml(path):
    """Read the first part of a MusicXML file. Returns (title, list of measures)."""
    return _read_root(_load_musicxml(path))


def _read_root(root):
    title = ""
    for title_path in (("work", "work-title"), ("movement-title",)):
        el = root
        for name in title_path:
            el = _child(el, name) if el is not None else None
        if el is not None and (el.text or "").strip():
            title = el.text.strip()
            break

    part = _child(root, "part")
    measures = []
    for measure in part:
        if _local(measure.tag) != "measure":
            continue
        notes = []
        for el in measure:
            if _local(el.tag) != "note":
                continue
            if _child(el, "chord") is not None:      # the flute plays one note at a time
                continue
            if _child(el, "rest") is not None:
                notes.append(Note())
                continue
            # tied note continuation: don't repeat the diagram
            ties = {c.get("type") for c in el if _local(c.tag) == "tie"}
            if "stop" in ties and "start" not in ties:
                continue
            pitch = _child(el, "pitch")
            if pitch is None:
                continue
            alter = _child(pitch, "alter")
            notes.append(Note(
                _child(pitch, "step").text.strip(),
                int(round(float(alter.text))) if alter is not None else 0,
                int(_child(pitch, "octave").text),
            ))
        # merge consecutive rests into one
        cleaned = []
        for n in notes:
            if n.is_rest and cleaned and cleaned[-1].is_rest:
                continue
            cleaned.append(n)
        if cleaned:
            measures.append(cleaned)
    return title, measures


# ---------------------------------------------------------------------------
# Plain text
# ---------------------------------------------------------------------------
NOTE_RE = re.compile(r"^([A-Ga-g])(##|bb|#|b|♯|♭|x)?(-?\d)$")
_ACCIDENTALS = {None: 0, "#": 1, "♯": 1, "b": -1, "♭": -1, "##": 2, "x": 2, "bb": -2}


def read_text(path):
    """Read the plain text format. Returns (title, list of measures).

    Example::

        title: Ode to Joy
        F#4 F#4 G4 A4 | A4 G4 F#4 E4 | D4 - D4 E4
    """
    title, measures, current = "", [], []
    text = Path(path).read_text(encoding="utf-8-sig")  # -sig: accept files with a BOM (Windows Notepad)
    for num, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
            continue
        for tok in line.replace("|", " | ").split():
            if tok == "|":
                if current:
                    measures.append(current)
                current = []
            elif tok in ("-", "r", "R"):
                current.append(Note())
            else:
                m = NOTE_RE.match(tok)
                if not m:
                    raise FingeringError(f"Line {num}: could not understand the note '{tok}'. "
                                         "Use something like C4, F#4, Bb5.")
                current.append(Note(m.group(1).upper(), _ACCIDENTALS[m.group(2)], int(m.group(3))))
        if current:  # the end of a line also closes the measure
            measures.append(current)
            current = []
    return title, measures


# ---------------------------------------------------------------------------
# Generic entry point
# ---------------------------------------------------------------------------
_ACCIDENTAL_NAMES = {-2: "flat-flat", -1: "flat", 1: "sharp", 2: "double-sharp"}


def measures_to_musicxml(title, measures):
    """Convert notes without rhythm (plain text format) into MusicXML: one quarter note per note."""
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<score-partwise version="4.0">',
           f'<work><work-title>{html.escape(title)}</work-title></work>',
           '<part-list><score-part id="P1"><part-name print-object="no">Flute</part-name></score-part></part-list>',
           '<part id="P1">']
    previous_len = None
    for i, measure in enumerate(measures, 1):
        out.append(f'<measure number="{i}">')
        if i == 1 or len(measure) != previous_len:
            first = ('<divisions>1</divisions><key><fifths>0</fifths></key>' if i == 1 else "")
            clef = '<clef><sign>G</sign><line>2</line></clef>' if i == 1 else ""
            out.append(f'<attributes>{first}<time print-object="no"><beats>{len(measure)}</beats>'
                       f'<beat-type>4</beat-type></time>{clef}</attributes>')
            previous_len = len(measure)
        for n in measure:
            if n.is_rest:
                out.append('<note><rest/><duration>1</duration><type>quarter</type></note>')
                continue
            alter = f'<alter>{n.alter}</alter>' if n.alter else ""
            accidental = (f'<accidental>{_ACCIDENTAL_NAMES[n.alter]}</accidental>'
                          if n.alter in _ACCIDENTAL_NAMES else "")
            out.append(f'<note><pitch><step>{n.step}</step>{alter}<octave>{n.octave}</octave></pitch>'
                       f'<duration>1</duration><type>quarter</type>{accidental}</note>')
        if i == len(measures):
            out.append('<barline location="right"><bar-style>light-heavy</bar-style></barline>')
        out.append('</measure>')
    out.append('</part></score-partwise>')
    return "\n".join(out)


def _score_from_roots(roots):
    """Build a Score from one or more MusicXML roots (several = movements, joined in order)."""
    main = _first_part_only(roots[0])
    main_part = _child(main, "part")
    for extra in roots[1:]:
        for measure in _child(extra, "part"):
            if _local(measure.tag) == "measure":
                main_part.append(copy.deepcopy(measure))
    title, measures = _read_root(main)
    return Score(title, measures, ET.tostring(main, encoding="unicode"))


def read_score(path, audiveris=None):
    """Read any supported format, chosen by file extension. Returns a :class:`Score`.

    For PDF/images, Audiveris is used (see :mod:`flute_fingering.omr`) and the
    recognized score is saved next to the original as ``<name>_recognized.mxl``.
    """
    path = Path(path)
    if not path.exists():
        raise FingeringError(f"File not found: {path}")
    ext = path.suffix.lower()
    if ext in MUSICXML_EXTENSIONS:
        return _score_from_roots([_load_musicxml(path)])
    if ext in OMR_EXTENSIONS:
        from . import omr
        roots = []
        with omr.recognize(path, audiveris) as results:
            for i, mxl in enumerate(results):
                suffix = "" if i == 0 else f"_{i+1}"
                saved = path.with_name(f"{path.stem}_recognized{suffix}{mxl.suffix}")
                shutil.copyfile(mxl, saved)
                print(f"Recognized score saved to: {saved}")
                roots.append(_load_musicxml(mxl))
        print("Note: automatic recognition may get some notes wrong. Compare with the original.")
        return _score_from_roots(roots)
    title, measures = read_text(path)
    return Score(title, measures, measures_to_musicxml(title, measures))
