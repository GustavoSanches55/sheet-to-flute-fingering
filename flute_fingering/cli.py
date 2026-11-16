"""Command line: ``flute-fingering SCORE [-o output.html] [--open]``."""

import argparse
import re
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .errors import FingeringError
from .reader import read_score
from .render import render_html


def build_parser():
    ap = argparse.ArgumentParser(
        prog="flute-fingering",
        description="Annotate a score with concert flute fingering diagrams.",
        epilog="PDFs and images require Audiveris: winget install audiveris.org.Audiveris",
    )
    ap.add_argument("score", type=Path,
                    help=".musicxml/.xml/.mxl, .txt, or PDF/image file (.pdf .png .jpg ...)")
    ap.add_argument("-o", "--output", type=Path,
                    help="output HTML file (default: <score>_fingering.html)")
    ap.add_argument("--open", action="store_true", help="open the result in the browser")
    ap.add_argument("--audiveris", help="path to the Audiveris executable (PDF/images only)")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        title, measures = read_score(args.score, args.audiveris)
    except FingeringError as e:
        print(e, file=sys.stderr)
        return 1
    if not measures:
        print("No notes found in the score.", file=sys.stderr)
        return 1

    output = args.output or args.score.with_name(args.score.stem + "_fingering.html")
    title = title or re.sub(r"[-_]+", " ", args.score.stem).strip().title()
    output.write_text(render_html(title, measures), encoding="utf-8")
    total = sum(1 for m in measures for n in m if not n.is_rest)
    print(f"{total} notes annotated -> {output}")
    if args.open:
        webbrowser.open(output.resolve().as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
