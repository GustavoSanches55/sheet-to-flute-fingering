import unittest

from flute_fingering.notes import Note
from flute_fingering.render import RED, render_html, render_svg, svg_fingering


class TestRender(unittest.TestCase):
    def test_full_html(self):
        page = render_html("My <song>", [[Note("D", 0, 4), Note("E", 0, 4)]])
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn("My &lt;song&gt;", page)  # escaped title
        self.assertIn("<svg", page)

    def test_out_of_range_warning(self):
        svg, out_of_range = render_svg([[Note("C", 0, 7)]])
        self.assertEqual(out_of_range, {"C7"})
        self.assertIn("out of", svg)

    def test_highlights_changes(self):
        self.assertIn(RED, svg_fingering(frozenset({"T", "L1"}), {"L1"}, 50, 0))
        self.assertNotIn(RED, svg_fingering(frozenset({"T", "L1"}), set(), 50, 0))

    def test_g_sharp_key_only_when_used(self):
        self.assertNotIn("G♯ key", svg_fingering(frozenset({"T"}), set(), 50, 0))
        self.assertIn("G♯ key", svg_fingering(frozenset({"T", "Gs"}), set(), 50, 0))

    def test_foot_keys_only_for_low_notes(self):
        self.assertNotIn("(foot", svg_fingering(frozenset({"T", "Eb"}), set(), 50, 0))
        self.assertIn("(foot", svg_fingering(frozenset({"T", "C"}), set(), 50, 0))


if __name__ == "__main__":
    unittest.main()
