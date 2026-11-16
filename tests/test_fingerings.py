import unittest

from flute_fingering.fingerings import FINGERINGS, KEYS, MIDI_MAX, MIDI_MIN, fingering
from flute_fingering.notes import Note


class TestChart(unittest.TestCase):
    def test_full_range(self):
        """Every chromatic note from B3 to A6 has a fingering."""
        self.assertEqual(set(FINGERINGS), set(range(MIDI_MIN, MIDI_MAX + 1)))

    def test_only_known_keys(self):
        for midi, keys in FINGERINGS.items():
            self.assertTrue(keys <= set(KEYS), midi)

    def test_d4_all_closed_without_eb(self):
        self.assertEqual(fingering(Note("D", 0, 4)), {"T", "L1", "L2", "L3", "R1", "R2", "R3"})

    def test_enharmonics_match(self):
        self.assertEqual(fingering(Note("D", 1, 4)), fingering(Note("E", -1, 4)))
        self.assertEqual(fingering(Note("G", 1, 4)), fingering(Note("A", -1, 4)))

    def test_second_octave_repeats_first(self):
        for step, alter in [("E", 0), ("F", 0), ("F", 1), ("G", 0), ("A", 0), ("B", 0), ("C", 1)]:
            octave = 5 if step == "C" else 4
            self.assertEqual(fingering(Note(step, alter, octave)), fingering(Note(step, alter, octave + 1)))

    def test_d5_lifts_finger_1(self):
        self.assertNotIn("L1", fingering(Note("D", 0, 5)))
        self.assertIn("L1", fingering(Note("D", 0, 4)))

    def test_g_sharp_uses_pinky_key(self):
        self.assertIn("Gs", fingering(Note("G", 1, 4)))

    def test_out_of_range(self):
        self.assertIsNone(fingering(Note("A", 0, 3)))
        self.assertIsNone(fingering(Note("C", 0, 7)))


class TestNote(unittest.TestCase):
    def test_midi(self):
        self.assertEqual(Note("C", 0, 4).midi, 60)
        self.assertEqual(Note("A", 0, 4).midi, 69)
        self.assertEqual(Note("B", 1, 4).midi, 72)

    def test_names(self):
        self.assertEqual(Note("F", 1, 4).name(), "F♯4")
        self.assertEqual(Note("B", -1, 4).name(), "B♭4")
        self.assertTrue(Note().is_rest)


if __name__ == "__main__":
    unittest.main()
