import json
import requests
import pickle
import numpy as np

import matplotlib as mpl

"""mpl.use('pgf')
mpl.rcParams.update({

    "pgf.texsystem": "pdflatex",
    'font.family': 'serif',
    'font.size': 16,
    'text.usetex': True,
    'pgf.rcfonts': False,

})"""
mpl.rcParams.update(
    {
        "pgf.texsystem": "pdflatex",
        "font.family": "serif",
        "font.size": 16,
        "text.usetex": True,
        "pgf.rcfonts": False,
    }
)
import matplotlib.pyplot as plt
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


def get_target():
    load_file = get_path("default_load_file")
    with open(load_file, "rb") as f:
        data = pickle.load(f)
    times = data["time"][1:]
    load_series = data["Lastreihe"][1:]
    result = []
    for time, load in zip(times, load_series):
        if time >= 87300:
            break
        load = load / 1000000
        result.append(load)
    print(len(result))
    result = [target for target in result for i in range(15)]
    return result


def calculate_power_curve(data, inverse=False):
    result = []
    if inverse:
        for i in range(len(data)):
            result.append(
                (
                    data[i]["fields"][P_el_BHKW]
                    + data[i]["fields"][P_el_PEM]
                    - data[i]["fields"][P_el_BAT]
                )
                / 1000000
            )
        return result
    for i in range(len(data)):
        result.append(
            (
                data[i]["fields"][P_el_BHKW]
                + data[i]["fields"][P_el_PEM]
                + data[i]["fields"][P_el_BAT]
            )
            / 1000000
        )
    return result


def plot_mosaik_result_curves(
    milp_curve, miqp_curve, gleam_curve, target, name="mosaik_plot.png"
):

    x = range(0, len(target))
    # plt.style.use("seaborn")
    plt.clf()
    # plt.subplots_adjust(bottom=1)
    plt.tight_layout(rect=(8, 8, 8, 8), h_pad=10)
    plt.gcf().subplots_adjust(bottom=0.15)

    plt.step(
        x,
        target,
        label="Target",
        color=matplotlib.colormaps["tab20"].colors[5],
        linewidth=1.5,
    )
    if milp_curve:
        plt.step(
            x,
            milp_curve,
            label="MILP",
            color=matplotlib.colormaps["tab20"].colors[2],
            linewidth=1.3,
            linestyle=(0, (1, 1)),
        )

    if miqp_curve:
        plt.step(
            x,
            miqp_curve,
            label="MIQP",
            color=matplotlib.colormaps["tab20"].colors[6],
            linewidth=1.3,
            linestyle=(0, (1, 1)),
        )

    plt.step(x, gleam_curve, label="EA", color="black", linewidth=1.3, linestyle="--")

    # plt.plot(x, milp_soc, label="MILP SOC")
    # plt.plot(x, gleam_soc, label="EA SOC")
    plt.legend()

    plt.xlabel("Timestep ")
    plt.ylabel("Power [MW]")
    plt.savefig(name, dpi=1000)

    RMSD(target, gleam_curve)
    if milp_curve:
        RMSD(target, milp_curve)
