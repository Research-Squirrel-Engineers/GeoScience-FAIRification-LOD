"""Old-versus-new comparison pages for the paper figures (PNG collages). Old figures come from the LaTeX tree of the paper,
new ones from docu/img/paper. Usage: py visuals\\paper_compare.py <old-img-dir> [page]"""
from __future__ import annotations
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
NEW = REPO / "docu" / "img" / "paper"
OUT = NEW / "compare"
COLW = 1500
GREY, RUST = (107, 114, 128), (154, 52, 18)


def _font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _load(p: Path, w=COLW):
    im = Image.open(p).convert("RGBA")
    bg = Image.new("RGBA", im.size, "white"); bg.alpha_composite(im)
    im = bg.convert("RGB")
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def _column(items, colour):
    blocks = []
    for title, im in items:
        bar = Image.new("RGB", (COLW, 70), colour)
        ImageDraw.Draw(bar).text((18, 16), title, fill="white", font=_font(34))
        blocks += [bar, im, Image.new("RGB", (COLW, 40), "white")]
    col = Image.new("RGB", (COLW, sum(b.height for b in blocks)), "white")
    y = 0
    for b in blocks:
        col.paste(b, (0, y)); y += b.height
    return col


def page(name, heading, old, new):
    L, R = _column(old, GREY), _column(new, RUST)
    H = max(L.height, R.height) + 110
    im = Image.new("RGB", (2 * COLW + 90, H), "white")
    ImageDraw.Draw(im).text((30, 30), heading, fill="black", font=_font(44))
    im.paste(L, (30, 100)); im.paste(R, (COLW + 60, 100))
    OUT.mkdir(parents=True, exist_ok=True)
    im.save(OUT / f"{name}.png", optimize=True)
    return OUT / f"{name}.png"


def main(argv):
    old = Path(argv[0])
    p = page("compare-1-ci", "Old versus new, part 1: CI",
             [("OLD: Fig. 9 (CI instance)", _load(old / "fig09_instance_ci.png")),
              ("OLD: Fig. 8 and map_ci", _load(old / "fig08_ci_findspots_map.png")),
              ("OLD: map_ci", _load(old / "map_ci.png"))],
             [("NEW: paper-ci-eruption (a eruption, b age and ± ka)", _load(NEW / "paper-ci-eruption.png")),
              ("NEW: paper-ci-map (replaces both, with Eifel marking E1 to E3)", _load(NEW / "paper-ci-map.png"))])
    print(p)
    p = page("compare-5-fig2-sisal-map", "Old versus new, part 5: Fig. 2 and the SISAL map",
             [("OLD: Fig. 2 (pipeline outputs, eight panels)", _load(old / "fig02_pipeline_outputs.png")),
              ("OLD: map_sisal (305 points)", _load(old / "map_sisal.png"))],
             [("NEW: paper-fig2 (a to e EPICA, f to i SISAL, vertical age axis with MIS bands)", _load(NEW / "paper-fig2.png")),
              ("NEW: paper-sisal-map (365 caves, colour gradient by the oldest age, time bar with MIS strip)", _load(NEW / "paper-sisal-map.png"))])
    print(p)
    p = page("compare-2-coin-taxonomy", "Old versus new, part 2: Fig. 1 and Fig. 3",
             [("OLD: Fig. 1 (generated infographic)", _load(old / "fig01_coin_framework.jpg")),
              ("OLD: Fig. 3 (taxonomy)", _load(old / "fig03_taxonomy.png"))],
             [("NEW: paper-coin (drawn coin with a squirrel, same content)", _load(NEW / "paper-coin.png")),
              ("NEW: paper-taxonomy (47 geo-lod classes, CRM core class left of every extension class, domain stripes, nested leaves)", _load(NEW / "paper-taxonomy.png"))])
    print(p)
    p = page("compare-3-instances", "Old versus new, part 3: Fig. 4 and Fig. 5 (instance models)",
             [("OLD: Fig. 4 (EPICA instance)", _load(old / "fig04_instance_epica.png")),
              ("OLD: Fig. 5 (SISAL instance)", _load(old / "fig05_instance_sisal.png"))],
             [("NEW: paper-epica-instance (a one observation with the core, b catalogue)", _load(NEW / "paper-epica-instance.png")),
              ("NEW: paper-sisal-instance (a cave site, b one speleothem with dating)", _load(NEW / "paper-sisal-instance.png"))])
    print(p)
    p = page("compare-4-ontdoc-new", "Old versus new, part 4: Fig. 6 and Fig. 7 (documentation screenshots) and new figures",
             [("OLD: Fig. 6 (EPICA documentation screenshot)", _load(old / "fig06_epica_lod_html.png")),
              ("OLD: Fig. 7 (SISAL documentation screenshot)", _load(old / "fig07_sisal_lod_html.png"))],
             [("NEW: paper-crosswalk (replaces both, link to the online documentation)", _load(NEW / "paper-crosswalk.png")),
              ("NEW: paper-workflow (workflow of the pipeline, new for RC-6)", _load(NEW / "paper-workflow.png")),
              ("NEW: paper-crm-family (new)", _load(NEW / "paper-crm-family.png")),
              ("NEW: paper-linked-graph (new)", _load(NEW / "paper-linked-graph.png"))])
    print(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
