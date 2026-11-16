import unittest
from pathlib import Path

from flute_fingering.diagram import RED, svg_fingering
from flute_fingering.engrave import add_note_name_lyrics, engrave
from flute_fingering.notes import Note
from flute_fingering.reader import Score, measures_to_musicxml, read_score
from flute_fingering.render import render_html

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
THUMB = "Left thumb (B key)"  # appears once in every in-range diagram


class TestDiagram(unittest.TestCase):
    def test_highlights_changes(self):
        self.assertIn(RED, svg_fingering(frozenset({"T", "L1"}), {"L1"}, 50, 0))
        self.assertNotIn(RED, svg_fingering(frozenset({"T", "L1"}), set(), 50, 0))

    def test_g_sharp_key_only_when_used(self):
        self.assertNotIn("G♯ key", svg_fingering(frozenset({"T"}), set(), 50, 0))
        self.assertIn("G♯ key", svg_fingering(frozenset({"T", "Gs"}), set(), 50, 0))

    def test_foot_keys_only_for_low_notes(self):
        self.assertNotIn("(foot", svg_fingering(frozenset({"T", "Eb"}), set(), 50, 0))
        self.assertIn("(foot", svg_fingering(frozenset({"T", "C"}), set(), 50, 0))


class TestEngrave(unittest.TestCase):
    def test_one_diagram_per_note_and_ties_skipped(self):
        score = read_score(EXAMPLES / "ode_to_joy.musicxml")
        pages, out_of_range = engrave(score.musicxml)
        svg = "".join(pages)
        # 16 written notes, one of them is the continuation of a tie
        self.assertEqual(svg.count(THUMB), 15)
        self.assertEqual(out_of_range, set())

    def test_note_names_as_lyrics(self):
        xml = add_note_name_lyrics(measures_to_musicxml("t", [[Note("F", 1, 4), Note(), Note("B", -1, 4)]]))
        self.assertIn("F♯4", xml)
        self.assertIn("B♭4", xml)
        self.assertEqual(xml.count("<lyric"), 2)  # the rest gets no name

    def test_key_signature_is_applied(self):
        """An F written in a G major score is played as F♯ (E♭ key down, R3 down)."""
        xml = """<score-partwise version="4.0"><part-list><score-part id="P1"><part-name/></score-part></part-list>
        <part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>1</fifths></key>
        <time><beats>1</beats><beat-type>4</beat-type></time><clef><sign>G</sign><line>2</line></clef></attributes>
        <note><pitch><step>F</step><alter>1</alter><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
        </measure></part></score-partwise>"""
        svg = "".join(engrave(xml)[0])
        self.assertIn("F♯4", svg)

    def test_out_of_range(self):
        _, out_of_range = engrave(measures_to_musicxml("t", [[Note("C", 0, 7)]]))
        self.assertEqual(out_of_range, {"C7"})


class TestHtml(unittest.TestCase):
    def test_full_html(self):
        notes = [[Note("D", 0, 4), Note("E", 0, 4)]]
        page = render_html(Score("My <song>", notes, measures_to_musicxml("x", notes)))
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn("My &lt;song&gt;", page)  # escaped title
        self.assertEqual(page.count(THUMB), 2 + 1)  # two notes + the legend


if __name__ == "__main__":
    unittest.main()
