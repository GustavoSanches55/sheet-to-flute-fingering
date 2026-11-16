"""The final HTML page: title, legend and the engraved score with fingering diagrams."""

import html

from .diagram import LEGEND
from .engrave import engrave


def render_html(score):
    """Full HTML page for a :class:`~flute_fingering.reader.Score`."""
    pages, out_of_range = engrave(score.musicxml)
    warning = ""
    if out_of_range:
        warning = ("<p class='warning'>Notes outside this chart's range (B3 to A6): "
                   + ", ".join(sorted(out_of_range)) + ".</p>")
    safe_title = html.escape(score.title or "Fingering")
    body = "\n".join(pages)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{safe_title} – flute fingering</title>
<style>
  body {{ font-family: "Segoe UI", Arial, sans-serif; margin: 24px; color: #111; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #666; margin: 0 0 16px; }}
  details {{ margin-bottom: 18px; }}
  .warning {{ color: #a33; }}
  svg.score {{ max-width: 100%; height: auto; display: block; }}
  @media print {{ details {{ display: none; }} body {{ margin: 0; }} }}
</style>
</head>
<body>
<h1>{safe_title}</h1>
<p class="sub">Concert flute – standard fingerings (Boehm system)</p>
<details open><summary>How to read the diagram</summary>{LEGEND}</details>
{warning}
{body}
</body>
</html>"""
