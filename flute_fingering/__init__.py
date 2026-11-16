"""Automatic fingering charts for the concert flute.

Reads a score (MusicXML, plain text or PDF/image), engraves it with Verovio and
produces an HTML page with the fingering diagram under every note.

Library usage::

    from flute_fingering import read_score, render_html

    score = read_score("song.musicxml")
    page = render_html(score)
"""

__version__ = "0.2.0"

from .errors import FingeringError
from .fingerings import FINGERINGS, fingering
from .notes import Note
from .reader import Score, read_musicxml, read_score, read_text
from .render import render_html

__all__ = [
    "FINGERINGS", "FingeringError", "Note", "Score", "fingering", "read_musicxml",
    "read_score", "read_text", "render_html", "__version__",
]
