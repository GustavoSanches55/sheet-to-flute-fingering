"""Score reading: MusicXML (.musicxml/.xml/.mxl), plain text (.txt) and PDF/image."""

import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .errors import FingeringError
from .notes import Note

MUSICXML_EXTENSIONS = (".musicxml", ".xml", ".mxl")
OMR_EXTENSIONS = (".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")


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


def read_musicxml(path):
    """Read the first part of a MusicXML file. Returns (title, list of measures)."""
    path = Path(path)
    try:
        root = ET.fromstring(_read_xml_bytes(path))
    except (ET.ParseError, zipfile.BadZipFile) as e:
        raise FingeringError(f"Could not read the MusicXML file {path.name}: {e}") from e
    if _local(root.tag) != "score-partwise":
        raise FingeringError("Only 'score-partwise' MusicXML is supported "
                             "(the default for MuseScore, Finale, Sibelius...).")

    title = ""
    for title_path in (("work", "work-title"), ("movement-title",)):
        el = root
        for name in title_path:
            el = _child(el, name) if el is not None else None
        if el is not None and (el.text or "").strip():
            title = el.text.strip()
            break

    part = _child(root, "part")
    if part is None:
        raise FingeringError("No <part> found in the file.")

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
def read_score(path, audiveris=None):
    """Read any supported format, chosen by file extension. Returns (title, measures).

    For PDF/images, Audiveris is used (see :mod:`flute_fingering.omr`) and the
    recognized score is saved next to the original as ``<name>_recognized.mxl``.
    """
    path = Path(path)
    if not path.exists():
        raise FingeringError(f"File not found: {path}")
    ext = path.suffix.lower()
    if ext in MUSICXML_EXTENSIONS:
        return read_musicxml(path)
    if ext in OMR_EXTENSIONS:
        from . import omr
        title, measures = "", []
        with omr.recognize(path, audiveris) as results:
            for i, mxl in enumerate(results):
                suffix = "" if i == 0 else f"_{i+1}"
                copy = path.with_name(f"{path.stem}_recognized{suffix}{mxl.suffix}")
                shutil.copyfile(mxl, copy)
                print(f"Recognized score saved to: {copy}")
                t, m = read_musicxml(mxl)
                title = title or t
                measures += m
        print("Note: automatic recognition may get some notes wrong. Compare with the original.")
        return title, measures
    return read_text(path)
