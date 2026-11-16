"""Generate the SVG images used in the README.

Run from the repository root:

    python docs/generate_images.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flute_fingering.diagram import LEGEND  # noqa: E402
from flute_fingering.engrave import engrave  # noqa: E402
from flute_fingering.reader import read_score  # noqa: E402


def with_white_background(svg):
    """White background, so the drawing stays readable in GitHub's dark theme."""
    end_of_tag = svg.index(">", svg.index("<svg")) + 1
    return svg[:end_of_tag] + '<rect width="100%" height="100%" fill="#fff"/>' + svg[end_of_tag:]


def main():
    score = read_score(ROOT / "examples" / "ode_to_joy.musicxml")
    pages, _ = engrave(score.musicxml)
    (ROOT / "docs" / "example.svg").write_text(with_white_background(pages[0]), encoding="utf-8")
    (ROOT / "docs" / "legend.svg").write_text(with_white_background(LEGEND.strip()), encoding="utf-8")
    print("Generated docs/example.svg and docs/legend.svg.")


if __name__ == "__main__":
    main()
