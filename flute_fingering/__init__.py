"""Automatic fingering charts for the concert flute.

Reads a score (MusicXML, plain text or PDF/image) and produces an HTML page with
each note on the staff and its fingering diagram underneath.

Library usage::

    from flute_fingering import read_score, render_html

    title, measures = read_score("song.musicxml")
    page = render_html(title, measures)
"""

__version__ = "0.1.0"

from .errors import FingeringError
from .fingerings import FINGERINGS, fingering
from .notes import Note
from .reader import read_musicxml, read_score, read_text
from .render import render_html, render_svg

__all__ = [
    "FINGERINGS", "FingeringError", "Note", "fingering", "read_musicxml", "read_score",
    "read_text", "render_html", "render_svg", "__version__",
]
