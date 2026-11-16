import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from flute_fingering.errors import FingeringError
from flute_fingering.notes import Note
from flute_fingering.reader import _read_root, read_musicxml, read_score, read_text

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def names(measures):
    return [[("-" if n.is_rest else n.name()) for n in m] for m in measures]


class TestText(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, content, encoding="utf-8"):
        p = self.folder / "t.txt"
        p.write_text(content, encoding=encoding)
        return p

    def test_basic(self):
        title, m = read_text(self.write("title: Test\nD4 F#4 | Bb4 - C5\n"))
        self.assertEqual(title, "Test")
        self.assertEqual(names(m), [["D4", "F♯4"], ["B♭4", "-", "C5"]])

    def test_comments_and_line_ends_close_measures(self):
        _, m = read_text(self.write("# comment\nD4 E4\nF4\n"))
        self.assertEqual(names(m), [["D4", "E4"], ["F4"]])

    def test_file_with_bom(self):
        """Windows Notepad sometimes saves with a BOM."""
        title, m = read_text(self.write("title: X\nD4\n", encoding="utf-8-sig"))
        self.assertEqual(title, "X")
        self.assertEqual(m[0][0], Note("D", 0, 4))

    def test_invalid_note(self):
        with self.assertRaises(FingeringError) as ctx:
            read_text(self.write("D4 H4\n"))
        self.assertIn("H4", str(ctx.exception))


class TestMusicXML(unittest.TestCase):
    def test_ode_to_joy_example(self):
        title, m = read_musicxml(EXAMPLES / "ode_to_joy.musicxml")
        self.assertIn("Ode to Joy", title)
        self.assertEqual(names(m)[0], ["F♯4", "F♯4", "G4", "A4"])
        # the tied F♯ in measure 4 is not repeated
        self.assertEqual(names(m)[3], ["F♯4", "E4"])
        self.assertEqual(names(m)[4], ["E4", "-"])

    def test_compressed_mxl(self):
        with tempfile.TemporaryDirectory() as folder:
            mxl = Path(folder) / "ode.mxl"
            with zipfile.ZipFile(mxl, "w") as z:
                z.writestr("META-INF/container.xml",
                           '<container><rootfiles><rootfile full-path="score.xml"/></rootfiles></container>')
                z.write(EXAMPLES / "ode_to_joy.musicxml", "score.xml")
            self.assertEqual(read_musicxml(mxl), read_musicxml(EXAMPLES / "ode_to_joy.musicxml"))


class TestReadScore(unittest.TestCase):
    def test_text_becomes_musicxml(self):
        score = read_score(EXAMPLES / "scale_and_intervals.txt")
        self.assertEqual(names(score.measures)[0], ["D4", "E4"])
        self.assertEqual(score.note_count, 29)
        # the generated MusicXML reads back to the same notes
        title, measures = _read_root(ET.fromstring(score.musicxml))
        self.assertEqual(title, score.title)
        self.assertEqual(names(measures), names(score.measures))

    def test_musicxml_keeps_only_the_first_part(self):
        with tempfile.TemporaryDirectory() as folder:
            two_parts = Path(folder) / "duet.musicxml"
            text = (EXAMPLES / "ode_to_joy.musicxml").read_text(encoding="utf-8")
            part = text[text.index('<part id="P1">'):text.index("</part>") + len("</part>")]
            text = text.replace("</part-list>", '<score-part id="P2"><part-name>Piano</part-name></score-part></part-list>')
            text = text.replace("</score-partwise>", part.replace('id="P1"', 'id="P2"') + "</score-partwise>")
            two_parts.write_text(text, encoding="utf-8")
            score = read_score(two_parts)
        self.assertNotIn('id="P2"', score.musicxml)
        self.assertEqual(score.note_count, 15)

    def test_missing_file(self):
        with self.assertRaises(FingeringError):
            read_score("does_not_exist.musicxml")


if __name__ == "__main__":
    unittest.main()
