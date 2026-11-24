# File: plot_epica_from_tab.py
#
# Draws the EPICA Dome C figures. Nothing else: the RDF that used to be built
# here moved to epica_rdf.py in S2, together with the three records this
# script never covered. Both read the same .tab through epica_data.py, so a
# figure and a triple can no longer disagree about what the file said.
#
# Multi-panel plates over the five records are still to come; this file is
# unchanged in what it draws.
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FuncFormatter, FixedLocator
import matplotlib.transforms as transforms
from scipy.signal import savgol_filter

# Byte-identical SVG across runs. Two things vary otherwise: the <dc:date>
# in the SVG metadata, and the random ids matplotlib gives clip paths. The
# salt fixes the ids, metadata={"Date": None} at save time drops the date.
plt.rcParams["svg.hashsalt"] = "geo-lod"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ontology")
)
import epica_data as ed
import numpy as np
import epica_plates
import geo_lod_figures as st
from geo_lod_captions import CaptionFile


class Tee:
    """Writes to stdout and to a file at the same time."""

    def __init__(self, filepath):
        self.file = open(filepath, "w", encoding="utf-8", newline="\n")
        self.stdout = sys.stdout
        # The report holds box-drawing rules and delta signs, and the console
        # is not always what receives them: redirect the run to a file or to
        # nul and Python falls back to the locale encoding, cp1252 on Windows,
        # which has no U+2500. The run then dies on its first section header,
        # before a single figure is written - and a byte-stability check that
        # redirects output would compare a file against itself.
        try:
            self.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        sys.stdout = self

    def write(self, data):
        self.stdout.write(data)
        self.file.write(data)

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        sys.stdout = self.stdout
        self.file.close()


# Set the working directory to the script's folder
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Output-Ordner erstellen
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "plots")
RDF_DIR = os.path.join(SCRIPT_DIR, "rdf")
ONTOLOGY_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "ontology")
REPORT_DIR = os.path.join(SCRIPT_DIR, "report")
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RDF_DIR, exist_ok=True)
os.makedirs(ONTOLOGY_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# Shared plot settings
# ──────────────────────────────────────────────
FIGURE_SIZE = (10, 30)
#: Screen dpi of the figure while it is being laid out. It is not the
#: resolution of the JPG - that comes from geo_lod_figures, which reads
#: it from the environment so that main.py --dpi can reach every
#: drawing script.
DPI = 100
LINE_COLOR = "black"
LINE_WIDTH = 1
GRID_COLOR = "#cccccc"
GRID_WIDTH = 1

# Y-axis ticks (depth in m)
DEPTH_MAJOR_TICK_INTERVAL = 500  # alle 500 m ein dicker Tick
DEPTH_MINOR_TICK_INTERVAL = 100  # alle 100 m ein kleiner Tick

# Y-axis ticks (age in ka BP)
AGE_MAJOR_TICK_INTERVAL = 100  # alle 100 ka ein dicker Tick
AGE_MINOR_TICK_INTERVAL = 20  # alle 20 ka ein kleiner Tick

FONT_SIZE_LABEL = 30
FONT_SIZE_TICK = 26
TITLE_FONTSIZE = 30
FONT_SIZE_MIS = 16

# Smoothing
ROLLING_WINDOW = 11  # Rolling median: window size in data points (~10 ka for CH4)
SG_WINDOW = 11  # Savitzky-Golay: window length (odd, ~10 ka for CH4)
SG_POLYORDER = 2  # Savitzky-Golay: polynomial order (2 = smooth, classic)
LINE_COLOR_FADED = "#aaaaaa"  # original line in smoothed plot
LINE_WIDTH_SMOOTH = 1.5  # smoothed line slightly thicker   # MIS label size
LABEL_PAD = 12

# ──────────────────────────────────────────────
# Axis overrides per dataset
# ──────────────────────────────────────────────
# The default is ticks derived from the data (epica_style.nice_ticks). Whoever
# wants to set an axis by hand enters it here - that is exactly what the dict
# is for, so that nobody writes a tick list into the plot call again and
# thereby silently cuts off measured values.
#
#   "log"      : logarithmic value axis
#   "ticks"    : fixed tick positions; the limits still enclose
#                the data in every case, so that nothing can drop out
#   "target"   : approximate number of intervals for the automatic division
AXIS_OVERRIDES: dict[str, dict] = {
    # Dust spans a factor of 560; on a linear axis nine tenths of it would be empty.
    "dust": {"log": True},
}

# ──────────────────────────────────────────────
# MIS bands
# ──────────────────────────────────────────────
# Boundaries and warm/cold come from dist/mis_stages.csv, that is, from the same
# source as the assignments in the graph (Railsback et al. 2015 as the guiding scheme).
# This used to be a list of its own after LR04, with two transitions adjusted by hand to the
# CH4 signal and without MIS 14. The figures change visibly as a
# result; this is the decision of 2026-08-09.
MIS_COLOR_WARM = "#fddbc7"
MIS_COLOR_COLD = "#d6e8f7"
MIS_LABEL_COLOR_WARM = "#8b1a00"
MIS_LABEL_COLOR_COLD = "#003f6b"


def draw_mis_bands(ax, y_min_ka, y_max_ka, covered=None, horizontal=False):
    """Draws the MIS bands on the age axis.

    covered  : optional sequence of ages of the actual measurement points. If it is
               given, stages without a single measured value get a
               dashed outline instead of a fill - so that a data gap
               can be recognised as a gap and not as a flat curve.
               Replaces the "nodata" entries formerly hard-coded for CH4.
    horizontal : True if the age is on the x-axis (row panels).
    """
    stages = ed.read_mis_stages()
    y_lo, y_hi = min(y_min_ka, y_max_ka), max(y_min_ka, y_max_ka)
    ages = sorted(covered) if covered is not None else None

    if horizontal:
        trans = transforms.blended_transform_factory(ax.transData, ax.transAxes)
    else:
        trans = transforms.blended_transform_factory(ax.transAxes, ax.transData)

    for st in stages:
        top, bot = st["end"], st["begin"]
        visible_top, visible_bot = max(top, y_lo), min(bot, y_hi)
        if visible_top >= visible_bot:
            continue

        warm = st["mode"] == "warm"
        color = MIS_COLOR_WARM if warm else MIS_COLOR_COLD
        label_color = MIS_LABEL_COLOR_WARM if warm else MIS_LABEL_COLOR_COLD

        has_data = True
        if ages is not None:
            has_data = any(top <= a < bot for a in ages)

        span = ax.axvspan if horizontal else ax.axhspan
        if has_data:
            span(top, bot, facecolor=color, alpha=1.0, zorder=0)
        else:
            span(
                top,
                bot,
                facecolor=color,
                alpha=0.35,
                edgecolor=label_color,
                linestyle=(0, (4, 3)),
                linewidth=1.2,
                zorder=0,
            )

        middle = (visible_top + visible_bot) / 2.0
        if horizontal:
            ax.text(
                middle, 0.985, st["label"], transform=trans, ha="center",
                va="top", fontsize=FONT_SIZE_MIS, fontweight="bold",
                color=label_color, rotation=90, zorder=2,
            )
        else:
            ax.text(
                0.99, middle, st["label"], transform=trans, ha="right",
                va="center", fontsize=FONT_SIZE_MIS, fontweight="bold",
                color=label_color, zorder=2,
            )


#: From this gap between two measurements on, the curve counts as interrupted.
#: The same value as ed.MAX_INTERPOLATION_GAP_KA, and deliberately so: a stretch
#: that appears as a gap in the figure is exactly the stretch over which the
#: generator interpolates no stage boundary.
GAP_THRESHOLD_KA = ed.MAX_INTERPOLATION_GAP_KA

FIGURE_LICENSE = "CC BY 4.0, Florian Thiery"

SMOOTHING_TEXT = {
    "": "The measured series is shown unsmoothed.",
    f"_smooth{ROLLING_WINDOW}": (
        f"A rolling median over {ROLLING_WINDOW} points is drawn in black over "
        f"the measured series in grey."
    ),
    f"_savgol{SG_WINDOW}p{SG_POLYORDER}": (
        f"A Savitzky-Golay filter over {SG_WINDOW} points at polynomial order "
        f"{SG_POLYORDER} is drawn in black over the measured series in grey."
    ),
}


def caption_for(meta, df, axis, suffix):
    """Caption of a single figure, from what was drawn."""
    n = len(df)
    if axis["key"] == "age_ka":
        span = (
            f"ages from {df['age_ka'].min():.1f} to {df['age_ka'].max():.1f} ka "
            f"on the {meta['trs']} scale"
        )
        bands = (
            "Marine Isotope Stage bands follow Railsback et al. (2015); a "
            "hatched band marks a stage without a measurement in this record."
        )
    else:
        span = (
            f"depths from {df['depth_m'].min():.1f} to {df['depth_m'].max():.1f} m"
        )
        bands = (
            f"Marine Isotope Stage bands are the boundaries of Railsback et al. "
            f"(2015) carried into depth by linear interpolation on the "
            f"{meta['trs']} scale; a stage whose boundary falls inside a data "
            f"gap carries no band."
        )
    return (
        f"{meta['label']} from the EPICA Dome C ice core, {n} measurements, "
        f"{span}. {SMOOTHING_TEXT[suffix]} {bands}"
    )


def _gap_edge_depth(df, age_ka, side):
    """Depth of the last measurement before, or the first after, the gap into which
    *age_ka* falls. Returns None if the age lies outside the measurement series.

    ``side="older"`` means: the edge sought is the older boundary of a
    stage, so the band ends at the last measurement *before* the gap.
    """
    pairs = sorted(zip(df["age_ka"].tolist(), df["depth_m"].tolist()))
    for (a0, d0), (a1, d1) in zip(pairs, pairs[1:]):
        if a0 <= age_ka <= a1:
            return d0 if side == "older" else d1
    return None


def mis_depth_bands_for(dataset_id, df):
    """MIS bands in depth for a dataset.

    Every stage boundary is published as an age. A depth for it arises only
    through interpolation in the depth-age model of this dataset - the same
    procedure that the generator uses for `geolod:MISBoundaryDepth`, and
    from the same function, so that figure and graph cannot drift
    apart.

    Three cases, distinguished since 2026-08-09:

    * Both boundaries interpolable - the band is drawn filled.
    * Only one boundary interpolable, because the other falls into a data gap
      - the band extends from the known edge to the end of the measurement series
      and is hatched. Previously it was dropped entirely; for CH4 this made
      MIS 7 and MIS 11 disappear, although one edge of each is known.
    * Neither - the stage lies completely within the gap, and there
      is no depth to which it could be assigned. For CH4 these are MIS 8 to 10.

    In addition, a neutral band over the gap itself. Without it there is only
    white space, and nothing else in this figure is white.
    """
    bands = []
    top_of_core = float(df["depth_m"].min())
    youngest = float(df["age_ka"].min())

    for st_ in ed.read_mis_stages():
        d_top = ed.interpolate_depth(df, st_["end"]) if st_["end"] > 0 else None
        d_bot = ed.interpolate_depth(df, st_["begin"])

        if d_top is None and st_["end"] <= youngest:
            # Youngest stage: the band begins at the topmost measurement point.
            d_top = top_of_core

        partial = False
        if d_top is None and d_bot is not None:
            d_top = _gap_edge_depth(df, st_["end"], "younger")
            partial = True
        elif d_bot is None and d_top is not None:
            d_bot = _gap_edge_depth(df, st_["begin"], "older")
            partial = True

        if d_top is None or d_bot is None or d_bot <= d_top:
            continue
        bands.append((d_top, d_bot, st_["label"], st_["mode"] == "warm", partial))

    return bands


def gap_bands_for(df):
    """The data gaps themselves, as neutral bands in depth."""
    pairs = sorted(zip(df["age_ka"].tolist(), df["depth_m"].tolist()))
    return [
        (d0, d1)
        for (a0, d0), (a1, d1) in zip(pairs, pairs[1:])
        if a1 - a0 > GAP_THRESHOLD_KA
    ]


def draw_mis_depth_bands(ax, bands, gaps=()):
    """Draws the precomputed depth bands."""
    trans = transforms.blended_transform_factory(ax.transAxes, ax.transData)

    for d_top, d_bot in gaps:
        ax.axhspan(d_top, d_bot, facecolor="#f2f2f2", edgecolor="#999999",
                   linestyle=(0, (4, 3)), linewidth=1.0, zorder=0)
        ax.text(
            0.99, (d_top + d_bot) / 2.0, "no samples", transform=trans,
            ha="right", va="center", fontsize=FONT_SIZE_MIS,
            fontstyle="italic", color="#777777", zorder=2,
        )

    for d_top, d_bot, label, warm, partial in bands:
        color = MIS_COLOR_WARM if warm else MIS_COLOR_COLD
        label_color = MIS_LABEL_COLOR_WARM if warm else MIS_LABEL_COLOR_COLD
        if partial:
            # Hatched: the stage extends beyond the edge of the measurement series,
            # where its depth is unknown.
            ax.axhspan(d_top, d_bot, facecolor=color, alpha=0.45,
                       edgecolor=label_color, linestyle=(0, (4, 3)),
                       linewidth=1.0, zorder=0)
        else:
            ax.axhspan(d_top, d_bot, facecolor=color, zorder=0)
        ax.text(
            0.99, (d_top + d_bot) / 2.0, label, transform=trans, ha="right",
            va="center", fontsize=FONT_SIZE_MIS, fontweight="bold",
            color=label_color, zorder=2,
        )


def create_plot(
    x_values,
    y_values,
    xlabel,
    ylabel,
    title_text,
    output_filename,
    y_major_interval,
    y_minor_interval,
    x_ticks=None,
    x_target=6,
    log_x=False,
    x_padding=0.05,
    invert_y=True,
    show_mis=False,
    mis_depth_bands=None,
    mis_depth_gaps=None,
    age_values=None,
    rolling_window=None,
    use_savgol=False,
):
    """
    Creates a standardised EPICA plot.

    x_values       : pd.Series  – the measurement quantity shown on the X-axis
    y_values       : pd.Series  – the depth / time shown on the Y-axis
    xlabel         : str        – X-axis label (LaTeX ok)
    ylabel         : str        – Y-axis label
    title_text     : str        – title above the plot
    output_filename: str        – full path without file extension
    y_major_interval: float    – major tick spacing Y
    y_minor_interval: float    – minor tick spacing Y
    x_ticks        : list|None – manual X-tick positions
    x_padding      : float     – relative X padding (if no manual ticks)
    invert_y       : bool      – invert Y-axis (depth increases downward)
    show_mis       : bool      – draw MIS bands and labels (age plots only)
    age_values     : pd.Series  – Alter der Messpunkte; nur zum Finden der
                                 Unterbrechungen, auch bei Tiefendarstellungen
    rolling_window : int|None  – window size for rolling median (None = no smoothing)
    use_savgol     : bool      – use Savitzky-Golay filter instead of rolling median
                                 (SG_WINDOW, SG_POLYORDER from config)
                                 If True: original line grey, smoothed line black
    """
    fig = plt.figure(figsize=FIGURE_SIZE, dpi=DPI)
    ax = fig.add_subplot(111)

    # Set Y-axis first (before MIS bands)
    y_min, y_max = y_values.min(), y_values.max()
    if invert_y:
        ax.set_ylim(y_max, y_min)
    else:
        ax.set_ylim(y_min, y_max)
    ax.margins(y=0)

    # MIS bands in background (zorder=0)
    if show_mis:
        # y_values here are the ages - so that the band function knows
        # which stages have any measured values in the dataset at all.
        draw_mis_bands(ax, y_min_ka=y_min, y_max_ka=y_max, covered=y_values)
    elif mis_depth_bands:
        draw_mis_depth_bands(ax, mis_depth_bands, mis_depth_gaps or ())

    # The curve, with gaps shown as gaps. The convention is taken from wdttest-sisal:
    # solid within a run, dashed across the
    # interruption, and the last sample before it, like the first after it, ringed.
    # Without it matplotlib draws a straight line across 178 ka without data, which
    # looks like a measured flat course.
    #
    # Interruptions are always searched for by age, also in the
    # depth views: a gap is a gap in the sampling, and whether
    # it looks large in metres depends only on the compression of the ice.
    breaks = st.find_breaks(np.asarray(age_values), GAP_THRESHOLD_KA)
    values = np.asarray(x_values, dtype=float)
    positions = np.asarray(y_values, dtype=float)

    if use_savgol or rolling_window is not None:
        # Raw values pale in the background, smoothed values on top.
        # The raw curve also gets rings and dashing. The ring marks
        # the last measured sample before the interruption - that is a
        # statement about the measurement series, not about the smoothing, and it applies
        # to both curves.
        st.draw_profile(ax, values, positions, breaks,
                        colour=LINE_COLOR_FADED, linewidth=LINE_WIDTH,
                        zorder=2)
        # Smoothed run by run, not across the interruption.
        if use_savgol:
            smooth = st.smooth_by_run(values, breaks, "savgol", SG_WINDOW,
                                      SG_POLYORDER)
        else:
            smooth = st.smooth_by_run(values, breaks, "median", rolling_window)
        st.draw_profile(ax, smooth, positions, breaks,
                        colour=LINE_COLOR, linewidth=LINE_WIDTH_SMOOTH,
                        zorder=3)
    else:
        st.draw_profile(ax, values, positions, breaks,
                        colour=LINE_COLOR, linewidth=LINE_WIDTH, zorder=2)

    ax.yaxis.set_major_locator(MultipleLocator(y_major_interval))
    ax.yaxis.set_minor_locator(MultipleLocator(y_minor_interval))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda val, pos: f"{int(val)}"))
    ax.grid(axis="y", which="major", color=GRID_COLOR, linewidth=GRID_WIDTH)
    ax.tick_params(axis="y", which="minor", length=4, width=0.8)

    # X-axis at the top
    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")

    # X-axis: ticks and limits from the data, not from a list in the code.
    # The limits always enclose the value range - the earlier fixed list
    # ended at 1.0 for d18O, where the data reach 1.457, and thereby cut
    # 82 of 1378 measured values out of the figure.
    x_min, x_max = float(x_values.min()), float(x_values.max())

    if log_x:
        ticks, (lo, hi) = st.log_ticks(x_min, x_max)
        ax.set_xscale("log")
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda val, pos: f"{val:g}")
        )
    else:
        if x_ticks is not None:
            ticks = list(x_ticks)
            lo = min(min(ticks), x_min)
            hi = max(max(ticks), x_max)
            pad = (hi - lo) * 0.04
            lo, hi = lo - pad, hi + pad
            step = ticks[1] - ticks[0] if len(ticks) > 1 else 1.0
            _, _, decimals = st.nice_ticks(lo, hi)
            if step == int(step):
                decimals = 0
        else:
            ticks, (lo, hi), decimals = st.nice_ticks(x_min, x_max, target=x_target)
        ax.xaxis.set_major_locator(FixedLocator(ticks))
        ax.set_xlim(lo, hi)
        ax.xaxis.set_major_formatter(
            FuncFormatter(lambda val, pos: st.format_tick(val, decimals))
        )

    # Labels
    ax.set_xlabel(xlabel, fontsize=FONT_SIZE_LABEL, labelpad=LABEL_PAD)
    ax.set_ylabel(
        ylabel, fontsize=FONT_SIZE_LABEL, labelpad=LABEL_PAD, fontweight="bold"
    )

    # Smoothing subtitle
    if use_savgol:
        subtitle = f"Savitzky-Golay filter  |  window = {SG_WINDOW} pts  |  polyorder = {SG_POLYORDER}"
    elif rolling_window is not None:
        subtitle = f"Rolling median filter  |  window = {rolling_window} pts"
    else:
        subtitle = "unsmoothed"

    # Titel oben (fett)
    ax.set_title(
        title_text,
        fontsize=TITLE_FONTSIZE,
        fontweight="bold",
        pad=8,
    )
    # Subtitle BELOW the x-axis label (negative y in figure coordinates)
    # We use ax.annotate with xycoords='axes fraction' and negative y
    ax.annotate(
        subtitle,
        xy=(0.5, -0.01),
        xycoords="axes fraction",
        ha="center",
        va="top",
        fontsize=TITLE_FONTSIZE * 0.55,
        fontstyle="italic",
        color="#777777",
    )

    ax.tick_params(axis="x", labelsize=FONT_SIZE_TICK)
    ax.tick_params(axis="y", labelsize=FONT_SIZE_TICK)

    # Saving - SVG through a handle opened in binary mode, otherwise Python writes
    # CRLF on Windows, while .gitattributes stores LF.
    st.save_figure(fig, output_filename)
    plt.close(fig)



def main():
    report_path = os.path.join(REPORT_DIR, "report.txt")
    tee = Tee(report_path)

    print("=" * 60)
    print("EPICA Dome C - figure generator (five records)")
    print("=" * 60)

    # All five datasets, both axes, three smoothing variants. Previously
    # twelve hand-written configurations for CH4 and d18O stood here;
    # the three other datasets did not appear in any single figure,
    # although they have been in the graph since S2.
    frames = {k: df for k, df in ed.load_all()}

    # One caption file per strand, collected in epica_plates.CAPTIONS: the
    # single figures enter their caption there, the plates likewise,
    # and writing happens once at the end. Two separate collectors would have
    # overwritten each other on writing.
    captions = epica_plates.CAPTIONS

    variants = [
        ("", {}),
        (f"_smooth{ROLLING_WINDOW}", {"rolling_window": ROLLING_WINDOW}),
        (f"_savgol{SG_WINDOW}p{SG_POLYORDER}", {"use_savgol": True}),
    ]

    n_total = len(ed.DATASET_ORDER) * 2 * len(variants)
    n = 0

    print("\n" + "-" * 60)
    print(f"Generating {n_total} single figures ...")
    print("-" * 60)

    for dataset_id in ed.DATASET_ORDER:
        meta = ed.DATASETS[dataset_id]
        df = frames[dataset_id]
        override = AXIS_OVERRIDES.get(dataset_id, {})
        xlabel = f"{meta['label']} [{meta['unit_label']}]"
        title = f"EPICA - {meta['label']}"

        depth_bands = mis_depth_bands_for(dataset_id, df)
        depth_gaps = gap_bands_for(df)

        axes = [
            {
                "key": "depth",
                "y": df["depth_m"],
                "ylabel": "Depth [m]",
                "y_major": DEPTH_MAJOR_TICK_INTERVAL,
                "y_minor": DEPTH_MINOR_TICK_INTERVAL,
                "show_mis": False,
                "mis_depth_bands": depth_bands,
                "mis_depth_gaps": depth_gaps,
            },
            {
                "key": "age_ka",
                "y": df["age_ka"],
                # According to A4: "Age [ka]", without BP or b2k. The reference point is
                # at the chronology node in the graph.
                "ylabel": "Age [ka]",
                "y_major": AGE_MAJOR_TICK_INTERVAL,
                "y_minor": AGE_MINOR_TICK_INTERVAL,
                "show_mis": True,
                "mis_depth_bands": None,
                "mis_depth_gaps": None,
            },
        ]

        for axis in axes:
            for suffix, opts in variants:
                n += 1
                name = f"{meta['short'].lower()}_vs_{axis['key']}_full{suffix}"
                print(f"\n[{n}/{n_total}] {title} - Y: {axis['ylabel']}")
                create_plot(
                    x_values=df["value"],
                    y_values=axis["y"],
                    xlabel=xlabel,
                    ylabel=axis["ylabel"],
                    title_text=f"{title}  ({meta['trs']})"
                    if axis["key"] == "age_ka"
                    else title,
                    output_filename=os.path.join(OUTPUT_DIR, name),
                    y_major_interval=axis["y_major"],
                    y_minor_interval=axis["y_minor"],
                    x_ticks=override.get("ticks"),
                    x_target=override.get("target", 6),
                    log_x=override.get("log", False),
                    show_mis=axis["show_mis"],
                    mis_depth_bands=axis["mis_depth_bands"],
                    mis_depth_gaps=axis["mis_depth_gaps"],
                    age_values=df["age_ka"],
                    **opts,
                )
                captions.add(
                    name,
                    caption=caption_for(meta, df, axis, suffix),
                    license=FIGURE_LICENSE,
                    sources=[meta["doi"]],
                )

    # The multi-part plates come beside the single files, not instead
    # of them: the single figure shows one curve large, the plate the
    # comparison that a single figure cannot provide.
    epica_plates.build_all()
    captions.write()

    print("\n" + "=" * 60)
    print(f"Done! {n_total} single figures plus the plates saved to '{OUTPUT_DIR}/'.")
    print(f"Report saved: {report_path}")
    print("=" * 60)
    tee.close()


if __name__ == "__main__":
    main()
