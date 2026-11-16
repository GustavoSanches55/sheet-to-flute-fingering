import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from flute_fingering import omr
from flute_fingering.errors import FingeringError
from flute_fingering.reader import read_score


class TestOMR(unittest.TestCase):
    def test_found_via_environment_variable(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / "Audiveris.exe"
            exe.write_text("")
            with mock.patch.dict(os.environ, {"AUDIVERIS": str(exe)}):
                self.assertEqual(omr.find_audiveris(), exe)

    def test_explicit_path_takes_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / "my_audiveris"
            exe.write_text("")
            self.assertEqual(omr.find_audiveris(str(exe)), exe)

    def test_missing_audiveris_explains_how_to_install(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / "song.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            with mock.patch.object(omr, "find_audiveris", return_value=None):
                with self.assertRaises(FingeringError) as ctx:
                    read_score(pdf)
            self.assertIn("winget install audiveris.org.Audiveris", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
