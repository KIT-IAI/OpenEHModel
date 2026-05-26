"""
Main script for running MILP/MIQP optimization and comparing with EA results.

This module orchestrates the optimization process, generates comparison plots,
and calculates statistics for different optimization approaches.
"""

import json
import logging
import os
import pickle
import sys
from typing import List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from config import get_path, get_optimization, get_output

import generate_loadts
from Daten.results import plotter
from schedule_generator import connect_and_schedule

logs_dir = get_path("logs_dir")
os.makedirs(logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, "optimization.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


opt_config = get_optimization()
TIMESTEPS_PER_DAY = opt_config.get("timesteps_per_day", 96)
TIMESTEP_SECONDS = opt_config.get("timestep_seconds", 900)
MW_CONVERSION_FACTOR = opt_config.get("mw_conversion_factor", 1000000)
TIMESTEP_DIVISOR = TIMESTEP_SECONDS // 60


class OptimizationConfig:
    """Configuration container for optimization parameters and file paths."""

    def __init__(self, n_days: int = 5):
        output_config = get_output()
        self.n_days = n_days
        output_dir = get_path("output_dir")
        os.makedirs(output_dir, exist_ok=True)
        self.all_results_file_quad = output_config.get(
            "all_results_quadratic", "output/all_results_quadratic_test.json"
        )
        self.all_results_file_lin = output_config.get(
            "all_results_linear", "output/all_results_lin_test.json"
        )
        self.result_schedule_file_quad = output_config.get(
            "schedule_quadratic", "output/res_sched_quad.csv"
        )
        self.result_schedule_file_lin = output_config.get(
            "schedule_linear", "output/res_sched_lin.csv"
        )

        self.ea_folder_path = get_path("ea_results_folder")
        self.timeseries_filename = get_path("timeseries_file")

        self.ea_results_filename = output_config.get(
            "ea_results", "output/ea_results.json"
        )
        self.ea_stats_filename = output_config.get("ea_stats", "output/ea_stats.txt")
        self.miqp_stats_filename = output_config.get(
            "miqp_stats", "output/miqp_stats.txt"
        )
        self.milp_stats_filename = output_config.get(
            "milp_stats", "output/milp_stats.txt"
        )


def load_ea_results(ea_results_folder: str) -> List[Tuple[List[float], List[float]]]:
    """
    Load and process EA results from JSON files.

    Args:
        ea_results_folder: Path to folder containing EA result JSON files

    Returns:
        List of tuples containing (combined_schedule, load_timeseries) for each day,
        both in MW units
    """
    ea_results = []
    json_files = [f for f in os.listdir(ea_results_folder) if f.endswith(".json")]

    for file in json_files:
        file_path = os.path.join(ea_results_folder, file)
        with open(file_path, "r", encoding="utf-8") as f:
            json_results = json.load(f)

        # Combine BHKW, Electrolyser, and Battery schedules
        combined_schedule = (
            np.array(json_results["BHKW"]["P_el"])
            + np.array(json_results["Electrolyseur"]["P_el"])
            - np.array(json_results["Battery"]["P"])
        )
        combined_schedule = combined_schedule / MW_CONVERSION_FACTOR

        ea_load_timeseries = (
            np.array(json_results["Lastreihe"]["P_el"]) / MW_CONVERSION_FACTOR
        )

        # Store trimmed results (remove last 2 timesteps from schedule, first 2 from load)
        ea_results.append([list(combined_schedule[:-2]), list(ea_load_timeseries[2:])])

    return ea_results


def save_ea_results(
    ea_results_list: List[Tuple[List[float], List[float]]],
    output_filename: str = "ea_results.json",
) -> None:
    """
    Save EA results to JSON file.

    Args:
        ea_results_list: List of EA results to save
        output_filename: Output file path
    """
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(ea_results_list, f, indent=2)


def generate_comparison_plots(
    ea_results_list: List[Tuple[List[float], List[float]]],
    comparison_result_file: str,
    filename_prefix: str = "ea_comparison",
    optimization_type: str = "MILP",
) -> None:
    """
    Generate comparison plots between EA and MILP/MIQP results.

    Args:
        ea_results_list: List of EA results (schedule, target) for each day
        comparison_result_file: Path to MILP/MIQP results JSON file
        filename_prefix: Prefix for output plot filenames
        optimization_type: Type of optimization ("MILP" or "MIQP") for legend label
    """
    with open(comparison_result_file, "r", encoding="utf-8") as f:
        miqp_results = json.load(f)

    for day_idx, (combined_schedule, ea_load_timeseries) in enumerate(ea_results_list):
        if day_idx >= len(miqp_results):
            break

        miqp_res_day = miqp_results[day_idx][0]
        ea_load_length = len(ea_load_timeseries[2:])

        # Align MIQP results with EA load length
        miqp_aligned = miqp_res_day[len(miqp_res_day) - ea_load_length :]

        plotter.generate_plot(
            [list(combined_schedule[:-2]), list(ea_load_timeseries[2:]), miqp_aligned],
            ["EA", "Target", optimization_type],
            filename=f"{filename_prefix}_day{day_idx}.pdf",
        )


def calculate_statistics(
    results_filename: str, stats_filename: str = "results_quadratic.txt"
) -> None:
    """
    Calculate and save RMSE statistics for optimization results.

    Args:
        results_filename: Path to results JSON file
        stats_filename: Output path for statistics text file
    """
    with open(results_filename, "r", encoding="utf-8") as f:
        result_list = json.load(f)

    rmses = []
    day_counter = 0

    for day in result_list:
        schedule, target = day[0], day[1]

        # Only calculate if dimensions match
        if len(target) != len(schedule):
            continue

        day_counter += 1

        # Calculate RMSE
        squared_errors = [(schedule[i] - target[i]) ** 2 for i in range(len(schedule))]
        mean_squared_error = sum(squared_errors) / len(schedule)
        rmse = np.sqrt(mean_squared_error)
        rmses.append(rmse)

    # Compile statistics
    stats = {
        "days": day_counter,
        "mean_rmse": np.mean(rmses) if rmses else 0,
        "std_rmse": np.std(rmses) if rmses else 0,
        "max_rmse": np.max(rmses) if rmses else 0,
        "95_percentile_rmse": np.percentile(rmses, 95) if rmses else 0,
        "98_percentile_rmse": np.percentile(rmses, 98) if rmses else 0,
    }

    # Write to file
    with open(stats_filename, "w", encoding="utf-8") as f:
        f.write(f"Statistics for {stats['days']} days\n")
        f.write(f"Mean RMSE: {stats['mean_rmse']}\n")
        f.write(f"Std RMSE: {stats['std_rmse']}\n")
        f.write(f"Max RMSE: {stats['max_rmse']}\n")
        f.write(f"95 percentile RMSE: {stats['95_percentile_rmse']}\n")
        f.write(f"98 percentile RMSE: {stats['98_percentile_rmse']}\n")


def prepare_timeseries(folder_path: str, output_filename: str, n_days: int) -> None:
    """
    Prepare and save timeseries data from EA results.

    Args:
        folder_path: Path to EA results folder
        output_filename: Output pickle file path
        n_days: Number of days to include in timeseries
    """
    load_ts_from_ea = generate_loadts.read_ea_results(folder_path)

    # Rename column for consistency
    load_ts_from_ea = load_ts_from_ea.rename(columns={"Lastreihe": "power"})

    # Truncate to specified number of days
    load_ts_from_ea = load_ts_from_ea.iloc[: n_days * TIMESTEPS_PER_DAY]

    # Normalize time column
    load_ts_from_ea["time"] = load_ts_from_ea["time"] / TIMESTEP_DIVISOR

    with open(output_filename, "wb") as f:
        pickle.dump(load_ts_from_ea, f)


def run_optimization(config: OptimizationConfig) -> None:
    """
    Execute complete optimization workflow.

    Args:
        config: OptimizationConfig instance with all parameters
    """
    # Prepare timeseries data
    logger.info("Preparing timeseries data...")
    prepare_timeseries(config.ea_folder_path, config.timeseries_filename, config.n_days)
    logger.info("Timeseries prepared: %s", config.timeseries_filename)

    # Run quadratic optimization
    logger.info("Running quadratic optimization...")
    connect_and_schedule(
        TIMESTEPS_PER_DAY,
        TIMESTEP_SECONDS,
        all_results_file=config.all_results_file_quad,
        result_schedule_file=config.result_schedule_file_quad,
        quadratic=True,
        load_ts=config.timeseries_filename,
        days=config.n_days,
        simpleplot=False,
    )
    logger.info(
        "Quadratic optimization completed. Results: %s", config.all_results_file_quad
    )

    # Run linear optimization
    logger.info("Running linear optimization...")
    connect_and_schedule(
        TIMESTEPS_PER_DAY,
        TIMESTEP_SECONDS,
        all_results_file=config.all_results_file_lin,
        result_schedule_file=config.result_schedule_file_lin,
        quadratic=False,
        load_ts=config.timeseries_filename,
        days=config.n_days,
        simpleplot=False,
    )
    logger.info(
        "Linear optimization completed. Results: %s", config.all_results_file_lin
    )

    # Process EA results
    logger.info("Processing EA results...")
    ea_results_list = load_ea_results(config.ea_folder_path)
    save_ea_results(ea_results_list, config.ea_results_filename)
    logger.info("EA results processed and saved: %s", config.ea_results_filename)

    # Calculate statistics
    logger.info("Calculating statistics...")
    calculate_statistics(config.all_results_file_quad, config.miqp_stats_filename)
    calculate_statistics(config.all_results_file_lin, config.milp_stats_filename)
    logger.info(
        "Statistics calculated. MIQP: %s, MILP: %s",
        config.miqp_stats_filename,
        config.milp_stats_filename,
    )

    # Generate comparison plots
    logger.info("Generating comparison plots...")
    generate_comparison_plots(
        ea_results_list, config.all_results_file_quad, "both", "MIQP"
    )
    generate_comparison_plots(
        ea_results_list, config.all_results_file_lin, "lin", "MILP"
    )
    logger.info("Comparison plots generated")

    logger.info("Optimization workflow completed successfully!")


def main():
    """Main entry point for the optimization script."""
    logger.info("Starting optimization workflow...")
    config = OptimizationConfig(n_days=5)
    try:
        run_optimization(config)
    except Exception as e:
        logger.error("Optimization workflow failed: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    main()
