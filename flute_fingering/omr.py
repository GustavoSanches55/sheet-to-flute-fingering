"""PDF/image recognition with Audiveris (optional external dependency).

Audiveris (https://github.com/Audiveris/audiveris) is a separate program; it is
only called here from the command line, in batch mode, to produce a MusicXML file.
"""

import contextlib
import os
import platform
import shutil
import subprocess
import tempfile
from pathlib import Path

from .errors import FingeringError

AUDIVERIS_INSTRUCTIONS = """\
Reading PDFs or images requires Audiveris (free, open source),
which was not found on this computer.

  Windows:  winget install audiveris.org.Audiveris
  Others:   https://github.com/Audiveris/audiveris/releases

If it is installed somewhere else, pass its path with
  --audiveris "C:\\path\\to\\Audiveris.exe"   (or set the AUDIVERIS environment variable)

Alternative without installing anything: open the PDF in MuseScore, export it as
MusicXML and use the .musicxml file with this program."""

MIN_IMAGE_WIDTH = 2000  # px; below this the staff lines are too close together for Audiveris
TIMEOUT = 900           # seconds


def find_audiveris(path=None):
    """Look for the executable: argument, AUDIVERIS variable, PATH and common install locations."""
    candidates = [path, os.environ.get("AUDIVERIS")]
    candidates += [shutil.which(n) for n in ("Audiveris", "audiveris")]
    system = platform.system()
    if system == "Windows":
        for base in filter(None, (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                                  os.environ.get("LOCALAPPDATA"))):
            candidates += [Path(base) / "Audiveris" / "Audiveris.exe",
                           Path(base) / "Audiveris" / "bin" / "Audiveris.bat",
                           Path(base) / "Programs" / "Audiveris" / "Audiveris.exe"]
    elif system == "Darwin":
        candidates += ["/Applications/Audiveris.app/Contents/MacOS/Audiveris"]
    else:
        candidates += ["/opt/audiveris/bin/Audiveris", "/usr/bin/audiveris", "/usr/local/bin/audiveris"]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    return None


def prepare_image(path, folder):
    """Upscale small images (e.g. screenshots), which Audiveris cannot read.

    Uses Pillow if installed (optional: ``pip install pillow``).
    Returns (path to use, warning or None).
    """
    if path.suffix.lower() == ".pdf":
        return path, None
    try:
        from PIL import Image
    except ImportError:
        return path, ("If the image is small (e.g. a screenshot), recognition may fail.\n"
                      "Install Pillow (pip install pillow) to upscale it automatically.")
    with Image.open(path) as im:
        width = im.width
        if width >= MIN_IMAGE_WIDTH:
            return path, None
        factor = MIN_IMAGE_WIDTH * 1.25 / width
        upscaled = im.convert("L").resize((round(width * factor), round(im.height * factor)), Image.LANCZOS)
    target = Path(folder) / (path.stem + ".png")
    upscaled.save(target)
    print(f"Small image ({width} px wide): upscaled {factor:.1f}x for recognition.")
    return target, None


@contextlib.contextmanager
def recognize(path, audiveris=None):
    """Run Audiveris and provide the list of generated MusicXML files (one per movement).

    Usage::

        with recognize(Path("song.pdf")) as files:
            ...

    Temporary files are deleted when the ``with`` block exits.
    """
    executable = find_audiveris(audiveris)
    if executable is None:
        raise FingeringError(AUDIVERIS_INSTRUCTIONS)

    folder = Path(tempfile.mkdtemp(prefix="flute_fingering_omr_"))
    try:
        inputs = folder / "input"
        inputs.mkdir()
        source, warning = prepare_image(Path(path), inputs)
        output = folder / "output"
        cmd = [str(executable), "-batch", "-export", "-output", str(output), "--", str(source.resolve())]
        print("Recognizing notes with Audiveris (this can take up to a minute per page)...")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            raise FingeringError(f"Audiveris took more than {TIMEOUT // 60} minutes and was stopped.")
        except OSError as e:
            raise FingeringError(f"Could not run Audiveris ({executable}): {e}")

        results = sorted(output.rglob("*.mxl")) or sorted(output.rglob("*.musicxml"))
        if not results:
            log = (proc.stdout + proc.stderr).strip().splitlines()
            raise FingeringError(
                "Audiveris could not recognize any score in this file.\n"
                "Tips: use a sharp, straight image with good resolution (300 dpi).\n"
                + (warning + "\n" if warning else "")
                + ("Last Audiveris messages:\n  " + "\n  ".join(log[-8:]) if log else ""))
        yield results
    finally:
        shutil.rmtree(folder, ignore_errors=True)
