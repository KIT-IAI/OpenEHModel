import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import json
import pickle
import os
import sys

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from config import get_path


def get_target(length=96):
    load_file = get_path("default_load_file")
    with open(load_file, "rb") as f:
        data = pickle.load(f)
    times = data["time"]  # [1:]
    load_series = data["Lastreihe"]  # [1:]
    result = []
    for i in range(length):
        result.append(load_series[i] / 1000000)  # convert to MW

    return result


def calculate_curve(data):
    gleam_curve = []
    electrolyser = data["Electrolyseur"]
    battery = data["Battery"]
    bhkw = data["BHKW"]
    for i in range(0, 96):
        gleam_curve.append(
            (electrolyser["P_el"][i] + battery["P"][i] + bhkw["P_el"][i]) / 1000000
        )
    return gleam_curve


def plot_load_comparison(milp, milp_ems, systemvalues):
    df_target = milp_ems["Lastreihe"]["P_el"]
    df_target = [target / 1000000 for target in df_target]
    target2 = get_target()
    milp_ems = calculate_curve(milp_ems)
    print(len(target2), len(milp_ems), len(df_target))
    generate_plot([milp, milp_ems, df_target], ["MILP", "EA", "Target"])


def generate_plot(curves, labels, filename):
    rc_fonts = {
        "text.usetex": True,
        # "font.family": "serif",
        "text.latex.preamble": r"""
        \usepackage{libertine}
        \usepackage[libertine]{newtxmath}
    """,
    }
    rc_fonts_old = {
        "text.usetex": True,
        # "font.family": "serif",
        "text.latex.preamble": r"""
            \usepackage{dsfont}
        \usepackage{biolinum}
        \setmainfont{Linux Biolinum O}
        \setsansfont{Linux Biolinum O}
        \renewcommand\familydefault{\sfdefault}
        \usepackage{cmbright}
        """,
    }
    rc_fonts = {
        "text.usetex": True,
        "svg.fonttype": "none",
        "font.family": "sans-serif",
        "pgf.preamble": r"""\usepackage[ttscale = 0.85]{libertine}
\usepackage
[
    libertine,    % Changes the math font to libertine (the main font).
    slantedGreek, % Makes all greek letters italic by default. If you want to use an upright greek letter, use ›\up‹ immediately followed by the letter’s name. For example, \upGamma displays an upright uppercase gamma.
    vvarbb,       % Changes the \mathbb font to another font. However, \mathbb remains ugly and should not be used. Use \mathds instead.
    libaltvw,     % Uses different characters for v und w that look far better than the default ones.
]
{newtxmath}
        \renewcommand\familydefault{\sfdefault}""",
        "text.latex.preamble": r"""\usepackage[ttscale = 0.85]{libertine}
\usepackage
[
    libertine,    % Changes the math font to libertine (the main font).
    slantedGreek, % Makes all greek letters italic by default. If you want to use an upright greek letter, use ›\up‹ immediately followed by the letter’s name. For example, \upGamma displays an upright uppercase gamma.
    vvarbb,       % Changes the \mathbb font to another font. However, \mathbb remains ugly and should not be used. Use \mathds instead.
    libaltvw,     % Uses different characters for v und w that look far better than the default ones.
]
{newtxmath}
\renewcommand\familydefault{\sfdefault}""",
        "font.size": 12,
        #'font.family': 'Linux Biolinum',
        #'font.family': 'libertine',
        "pgf.rcfonts": False,
    }

    matplotlib.rcParams.update(rc_fonts)
    plt.rcParams.update(rc_fonts)
    x = range(0, len(curves[0]))
    # plt.style.use("seaborn-v0_8")
    plt.clf()
    # read all ttf files
    path = "C:\\Users\\cy2814\\Downloads\\LinLibertineTTF_5.3.0_2012_07_02\\LinLibertineTTF_5.3.0_2012_07_02"
    font_files = matplotlib.font_manager.findSystemFonts(fontpaths=[path])
    for font_file in font_files:
        matplotlib.font_manager.fontManager.addfont(font_file)

    # plt.rcParams.update({'hatch.linewidth':500})
    # plt.rcParams.update({'font.size': 12})
    plt.figure(figsize=(7, 5))

    for curve, label in zip(curves, labels):
        if label == "Target":
            plt.step(
                x,
                curve,
                label=label,
                color="#F7A726",
                linestyle="dashed",
                linewidth=1,
                markersize=12,
            )  # "#a6d854" "#2020ff9c"
        elif label == "eatest":
            plt.step(
                x,
                curve,
                label=label,
                color="blue",
                linestyle="--",
                linewidth=1,
                markersize=12,
            )
        elif "MILP" in label or "MIQP" in label:
            plt.step(
                x,
                curve,
                label=label,
                color="#191970",
                linestyle="dotted",
                linewidth=1,
                markersize=12,
            )  # "#ff8103"
        else:
            plt.step(
                x, curve, color="#CE5056", label=label, linewidth=1, markersize=12
            )  # "#c8435d" "#c8435d"
    # plt.plot(x, get_target(), label="Target", linestyle="--")
    plt.xlabel("Timestep ")
    plt.ylabel("Power [MW]")

    plt.legend()
    output_dir = get_path("output_dir")
    plt.savefig(os.path.join(output_dir, filename))
    plt.close()
    # plt.show()
