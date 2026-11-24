#!/usr/bin/env python3
"""paper_page.py - docu/paper.html: the figures of the paper with their captions (paper_captions.yaml), the interactive
SISAL time map for the reviewers, and, for the time of the revision only, the old-versus-new comparison images.

Run it through `py visuals/build.py --only paper`. The output is deterministic: sorted comparison images, no date.
The comparison section is temporary: delete docu/img/paper/compare/ and the COMPARE block below when the revision is done.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

import site_kit as K  # noqa: E402

DOCU = REPO / "docu"
IMG = DOCU / "img" / "paper"
CREDIT = "Fiona Schenk, Florian Thiery, Research Squirrel Engineers at LEIZA. CC BY 4.0."


def build() -> int:
    items = yaml.safe_load((HERE / "paper_captions.yaml").read_text(encoding="utf-8"))["figures"]
    missing = [i["name"] for i in items if not (IMG / f"{i['name']}.png").exists() or not (IMG / f"{i['name']}.svg").exists()]
    if missing:
        raise SystemExit("figures missing in docu/img/paper/: " + ", ".join(missing) + " (run visuals/paper_figs.py)")
    cards = []
    for i in items:
        card = K.fig_card(IMG, i["name"], i["label"], " ".join(str(i["caption"]).split()), CREDIT, href_dir="img/paper")
        cards.append(card.replace("</section>", f'<p class="cr">Replaces: {K.esc(i["replaces"])}</p>\n</section>'))
    body = "\n".join(cards)
    if (IMG / "paper-sisal-timemap.html").exists():
        body += ('\n<section class="text"><h2>Interactive map for the reviewers</h2><p><a href="img/paper/paper-sisal-timemap.html">'
                 "SISAL caves through time</a>: a slider over 0 to 500 ka BP; a cave is lit when the age lies within the span of its "
                 "published age model. The span marks where a record begins and ends, hiatuses lie inside it.</p></section>")
    comp = sorted((IMG / "compare").glob("*.png")) if (IMG / "compare").exists() else []
    if comp:
        body += ('\n<section class="text"><h2>Temporary: old versus new</h2><p>For the revision only. Top row: the figures of the '
                 "submitted paper, bottom row: the new ones.</p>"
                 + "".join(f'<p><a href="img/paper/compare/{c.name}"><img src="img/paper/compare/{c.name}" width="{K.png_size(c)[0]}" '
                           f'height="{K.png_size(c)[1]}" loading="lazy" alt="{K.esc(c.stem)}" style="max-width:100%;height:auto"></a></p>' for c in comp)
                 + "</section>")
    intro = ("The figures of the paper with their captions, rebuilt from the graphs of this repository by "
             "<code>visuals/paper_figs.py</code>. The captions are drafts for the revision and live in <code>visuals/paper_captions.yaml</code>; "
             'the classes and properties behind them are in the <a href="index.html">documentation</a>.')
    K.write_assets(DOCU)
    K.write_page(DOCU / "paper.html", K.page("docu", "paper.html", "Paper figures", intro, body))
    print(f"docu/paper.html: {len(items)} figures, {len(comp)} comparison images")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
