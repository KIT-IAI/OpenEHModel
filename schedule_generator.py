import json
import logging
import os
import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_path, get_solver, get_optimization, get_weights, get_constraints
from pyomo.opt import SolverFactory

from components.target import Target
from components.heat_target import HeatTarget
from components.grid import Grid
from components.converter import Converter
from components.storage import Storage
from load_import import load_obj
from indexed_model import IndexedModel
from Daten.results.plotter import generate_plot
import Daten.results.mosaik_plotter as mosaik_plotter
import utils.result_schedule_handler

# Configure logging
logger = logging.getLogger(__name__)

# Module-level constants for backward compatibility
facility_names = ["chp", "pem", "bat", "meth", "heat_pump"]
name_to_id = {
    "chp": "1",
    "pem": "2",
    "bat": "3",
    "Gasstorage": "4",
    "meth": "6",
    "Lastreihe": "10",
}


def load_facility_parameters():
    """Load facility parameters and constants from JSON file."""
    json_file_path = os.path.join(os.path.dirname(__file__), "facility_parameters.json")
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


# Load constants at module level
_config = load_facility_parameters()
CONSTANTS = _config["constants"]

# Extract constants for backward compatibility
METHANE_ENERGY = CONSTANTS["METHANE_ENERGY"]
H2_ENERGY = CONSTANTS["H2_ENERGY"]
INCOME_WEIGHT = CONSTANTS["INCOME_WEIGHT"]
FULFILLMENT_WEIGHT = CONSTANTS["FULFILLMENT_WEIGHT"]
pr_CO2 = CONSTANTS["pr_CO2"]
CH4_to_CO2 = CONSTANTS["CH4_to_CO2_factor"] / METHANE_ENERGY
H2_TO_METHANE = CONSTANTS["H2_TO_METHANE"] * H2_ENERGY * 62.3 / (METHANE_ENERGY * 496)
PEAK_RMSD = CONSTANTS["PEAK_RMSD"]
MIN_INCOME = CONSTANTS["MIN_INCOME"]
MAX_INCOME = CONSTANTS["MAX_INCOME"]


class ScheduleGenerator:
    """
    Encapsulates all scheduling and optimization logic for the energy hub system.

    This class manages the creation of optimization models, solving them with various
    configurations, and extracting schedules from the results.
    """

    def __init__(self, timeframe=96, step_length=15 * 60, ipopt_executable=None):
        """
        Initialize the ScheduleGenerator.

        Args:
            timeframe (int): Number of time steps in the optimization horizon.
            step_length (int): Duration of each time step in seconds.
            ipopt_executable (str, optional): Path to IPOPT executable. If None, uses default.
        """
        self.timeframe = timeframe
        self.step_length = step_length
        solver_config = get_solver()
        self.ipopt_executable = solver_config.get("ipopt_executable", "ipopt")
        self.facility_params = self._get_facility_parameters_dict()

    @staticmethod
    def _get_facility_parameters_dict():
        """Extract facility parameters excluding constants."""
        params = load_facility_parameters()
        return {k: v for k, v in params.items() if k != "constants"}

    def get_gas_price(self):
        """Load and interpolate gas prices to match timeframe and step length."""
        data = load_obj(get_path("gas_demand_file"))
        times = data["time"]
        prices = data["Price"]
        result = []
        prev_time = 0
        for timestamp, price in zip(times, prices):
            while (
                prev_time < timestamp and prev_time < self.timeframe * self.step_length
            ):
                result.append(price * 1000)  # €/mwh to €/kwH
                prev_time += self.step_length
            if prev_time > self.timeframe * self.step_length:
                break
        logger.debug("Gas prices loaded: %s timesteps", len(result))
        return result

    def get_electricity_price(self, start_time=0):
        """Load and interpolate electricity prices to match timeframe and step length."""
        data = load_obj(get_path("electricity_price_file"))
        times = data["time"]
        prices = data["price"]
        times = [t for t in times if t >= start_time]
        prices = prices[len(prices) - len(times) :]
        result = []
        prev_time = start_time
        for timestamp, price in zip(times, prices):
            while (
                prev_time <= timestamp
                and prev_time < start_time + self.timeframe * self.step_length
            ):
                result.append(price)  # €/mwH
                prev_time += self.step_length
            if prev_time > start_time + self.timeframe * self.step_length:
                break
        return result

    def get_heat_demand(self):
        """Load and prepare heat demand series from config path."""
        try:
            data = load_obj(get_path("heat_demand_file"))
            logger.debug("Heat demand series loaded from Heat_Demand_Series.pkl")

            # Extract heat demand from the pickle file
            if isinstance(data, dict) and "heat_demand_series" in data:
                heat_series = data["heat_demand_series"]
            elif isinstance(data, (list, tuple)):
                heat_series = data
            else:
                logger.warning(
                    "Unexpected data structure in Heat_Demand_Series.pkl, using empty series"
                )
                heat_series = [0.0] * self.timeframe

            # Ensure we have exactly timeframe values
            result = []
            for i in range(self.timeframe):
                if i < len(heat_series):
                    result.append(heat_series[i] / 10000)
                else:
                    # Pad with zeros if necessary
                    result.append(0.0)

            logger.debug("Heat demand prepared: %s timesteps", len(result))
            return result
        except FileNotFoundError:
            logger.warning("Heat_Demand_Series.pkl not found, using zero heat demand")
            return [0.0] * self.timeframe
        except Exception as e:
            logger.error("Error loading heat demand series: %s", e, exc_info=True)
            return [0.0] * self.timeframe

    def build_model(self, load_timeseries=None):
        """
        Build and return an optimized model.

        Args:
            load_timeseries (list, optional): Target load timeseries. If None, loads from default file.

        Returns:
            IndexedModel: The configured Pyomo model.
        """
        logger.debug("Building model from facility parameters")
        model = self._model_from_facility_parameters()
        logger.debug("Adding prices to model")
        model = self._add_prices_to_model(model)

        if load_timeseries:
            logger.debug(
                "Using provided load timeseries with %s timesteps", len(load_timeseries)
            )
            electricity_prices = self.get_electricity_price()
            complete_load = {}
            for ts in range(len(load_timeseries)):
                complete_load[ts] = -1 * load_timeseries[ts]
            target = Target(
                "target",
                time_series=complete_load,
                types=["electricity"],
                electricity_prices=electricity_prices,
                step_length=self.step_length,
            )
            model.add_device(target)

            # Also add heat target
            heat_demand = self.get_heat_demand()
            heat_target = HeatTarget(
                "heat_target",
                time_series=heat_demand,
                step_length=self.step_length,
            )
            model.add_device(heat_target)
            logger.debug(
                "Heat target added to model with %s timesteps", len(heat_demand)
            )
        else:
            logger.debug("Loading default load timeseries")
            model = self._add_target_to_model(model)
        logger.debug("Model build completed")
        return model

    def _model_from_facility_parameters(self):
        """Create model with facility parameters."""
        model = IndexedModel(index=range(0, self.timeframe))
        logger.debug("Creating IndexedModel for optimization")

        heat_price = self.get_gas_price()
        chp_params = self.facility_params["BHKW"]["metadata"]
        chp = Converter(
            name="chp",
            max_powers={"electricity": chp_params["P_max_KWK"] / 1000000},
            min_powers={"electricity": chp_params["P_min_KWK"] / 1000000},
            conversion_factors={"methane": 0.43, "electricity": 1},
            input_types=["methane"],
            output_types=["electricity"],
            ramp_up=chp_params["t_startup"],
            ramp_down=1,
            heat_price=heat_price,
            is_chp=True,
            thermic_efficiency=0.423,
            pr_CO2=pr_CO2,
            CH4_to_CO2=CH4_to_CO2,
            step_length=self.step_length,
        )
        model.add_device(chp)
        logger.debug("Added CHP converter")

        electrolysis_params = self.facility_params["pem"]
        electrolysis = Converter(
            name="pem",
            max_powers={
                "h2": electrolysis_params["input"]["Eta_PEM"]
                * electrolysis_params["input"]["P_max_PEM"]
                / 1000000
            },
            min_powers={"h2": 0.31 * 0.73},
            conversion_factors={
                "h2": 1,
                "electricity": electrolysis_params["input"]["Eta_PEM"],
            },
            input_types=["electricity"],
            output_types=["h2"],
            ramp_up=electrolysis_params["input"]["t_ramp_PEM"],
            ramp_down=1,
            step_length=self.step_length,
        )
        model.add_device(electrolysis)
        logger.debug("Added PEM electrolyzer")

        meth_params = self.facility_params["Methanation"]
        meth = Converter(
            name="meth",
            max_powers={"methane": (meth_params["input"]["P_max_meth"]) / 1000000},
            min_powers={"methane": meth_params["input"]["P_min_meth"] / 1000000},
            input_types=["h2"],
            output_types=["methane"],
            ramp_up=meth_params["input"]["t_ramp_meth"],
            ramp_down=1,
            pr_CO2=pr_CO2,
            CH4_to_CO2=CH4_to_CO2,
            conversion_factors={
                "methane": 1,
                "h2": H2_TO_METHANE,
            },
            step_length=self.step_length,
        )
        model.add_device(meth)
        logger.debug("Added methanation converter")

        # Heat pump: ensure conversion factor maps so that electricity = -heat / COP
        # and include an (optional) electrical power bound for the input side
        heat_pump_params = self.facility_params["HP"]
        heat_meta = heat_pump_params.get("metadata", {})
        cop = heat_meta.get("COP_HP", heat_meta.get("COP", 3.0))
        q_max_w = heat_meta.get("P_max", heat_meta.get("Q_nominal", 200000))
        q_min_w = heat_meta.get("P_min", max(0.1 * q_max_w, heat_meta.get("P_min", 0)))
        # electrical input nominal (optional) - compute from Q_nominal/COP if not provided
        p_el_nom_w = heat_meta.get(
            "P_el_nominal", int(q_max_w / cop) if cop else int(q_max_w)
        )

        heat_pump = Converter(
            name="heat_pump",
            # max_powers/min_powers are provided for the output type 'heat' in MW
            max_powers={"heat": q_max_w / 1_000_000},
            min_powers={"heat": q_min_w / 1_000_000},
            # conversion_factors: for consistency with Converter.power_equality
            # -sum(output_power * conv_out) == sum(input_power * conv_in)
            # so set conv_out=1 and conv_in=COP, yielding electricity = -heat / COP
            conversion_factors={"electricity": cop, "heat": 1},
            input_types=["electricity"],
            output_types=["heat"],
            ramp_up=heat_meta.get("t_startup", 300),
            ramp_down=1,
            step_length=self.step_length,
        )
        model.add_device(heat_pump)
        logger.debug("Added heat pump converter")

        bat_params = self.facility_params["bat"]["input"]
        bat_cap = bat_params["EBat"] / 3_600_000_000
        bat = Storage(
            name="bat",
            max_charging_power=bat_params["P_max_Bat"] / 1_000_000,
            max_discharging_power=bat_params["P_max_Bat"] / 1_000_000,
            capacity=bat_cap,  # Joule to mwh
            initial_charge=bat_cap / 2,
            charging_efficiency=0.92,
            input_types=["electricity"],
            step_length=self.step_length,
        )
        model.add_device(bat)
        logger.debug("Added battery storage")

        gas_storage = Storage(
            name="Gasstorage",
            max_charging_power=0.27 * METHANE_ENERGY * self.step_length,
            max_discharging_power=0.27 * METHANE_ENERGY * self.step_length,
            capacity=1500 * METHANE_ENERGY,
            initial_charge=750 * METHANE_ENERGY,
            charging_efficiency=1,
            input_types=["methane"],
            step_length=self.step_length,
        )
        model.add_device(gas_storage)
        logger.debug("Added gas storage")
        return model

    def _add_prices_to_model(self, model):
        """Add pricing grids to the model."""
        gas_price = self.get_gas_price()
        gas_network = Grid(
            "gas_grid",
            max_buying_power=-1000,
            max_selling_power=1000,
            energy_cost=gas_price,
            types=["methane"],
            step_length=self.step_length,
        )
        model.add_device(gas_network)
        h2_price = [5.95 / H2_ENERGY for _ in range(self.timeframe)]
        h2_network = Grid(
            "h2grid",
            max_buying_power=-1000,
            max_selling_power=0,
            energy_cost=h2_price,
            types=["h2"],
            step_length=self.step_length,
        )
        model.add_device(h2_network)

        heat_network = Grid(
            "heat_grid",
            max_buying_power=-100000,
            max_selling_power=100000,
            energy_cost=gas_price,
            types=["heat"],
            step_length=self.step_length,
        )
        model.add_device(heat_network)
        return model

    def _add_target_to_model(self, model):
        """Add electricity and heat demand targets to the model."""
        data = load_obj(get_path("default_load_file"))
        times = data["time"]
        load_series = data["Lastreihe"]
        result = []
        for i in range(self.timeframe):
            result.append(-load_series[i] / 1000000)
        electricity_prices = self.get_electricity_price()

        target = Target(
            "target",
            time_series=result,
            types=["electricity"],
            electricity_prices=electricity_prices,
            step_length=self.step_length,
        )
        model.add_device(target)

        # Add heat target
        heat_demand = self.get_heat_demand()
        heat_target = HeatTarget(
            "heat_target",
            time_series=heat_demand,
            step_length=self.step_length,
        )
        model.add_device(heat_target)
        logger.debug("Heat target added to model with %s timesteps", len(heat_demand))

        return model

    def solve_model(
        self,
        model,
        income_weight,
        fulfillment_weight,
        max_mean_deviation,
        min_mean_deviation,
        min_income,
        max_income,
        quadratic=False,
    ):
        """
        Solve the optimization model.

        Args:
            model: The Pyomo model to solve.
            income_weight: Weight for income objective.
            fulfillment_weight: Weight for fulfillment objective.
            max_mean_deviation: Maximum mean deviation.
            min_mean_deviation: Minimum mean deviation.
            min_income: Minimum income.
            max_income: Maximum income.
            quadratic: Whether to use quadratic optimization.

        Returns:
            The solved model.
        """
        logger.debug("Setting objective weights and constraints")
        model.set_objective_with_weights(
            income_weight=income_weight,
            fulfillment_weight=fulfillment_weight,
            step_length=self.step_length,
            max_mean_deviation=max_mean_deviation,
            min_mean_deviation=min_mean_deviation,
            min_income=min_income,
            max_income=max_income,
            quadratic=quadratic,
        )
        logger.debug("Objective created")
        model.generate_power_balance()
        logger.debug("Power balance constraints created")

        solver = SolverFactory("ipopt", executable=self.ipopt_executable)
        logger.info("Starting solver (IPOPT)...")

        result = solver.solve(model, logfile=get_path("solver_log"))
        logger.info(f"Solver result: {result}")

        logger.info(
            f"Income DOF: {model.income_dof():.4f}, Sum: €{model.income_sum():.2f}"
        )
        logger.info(
            f"Fulfillment DOF: {model.fulfillment_dof():.4f}, Mean deviation: {model.mean_deviation():.4f} MWh²"
        )
        return model

    @staticmethod
    def extract_schedule_from_result(model):
        """Extract schedule from solved model."""
        schedule = {}
        for facility in facility_names:
            if facility == "bat":
                setpoints = [
                    value
                    for _, value in model.get_attribute_by_name(facility, "setpoint")
                    .extract_values()
                    .items()
                ]
                is_charging = [
                    value
                    for _, value in model.get_attribute_by_name(facility, "is_charging")
                    .extract_values()
                    .items()
                ]

                schedule[facility] = [
                    (-setpoint) if charging else (setpoint)
                    for (setpoint, charging) in zip(setpoints, is_charging)
                ]
            else:
                schedule[facility] = [
                    value
                    for _, value in model.get_attribute_by_name(facility, "setpoint")
                    .extract_values()
                    .items()
                ]
        return schedule

    def optimize_single_step(self):
        """Run single-step optimization."""
        model = self.build_model()
        model = self.solve_model(
            model,
            income_weight=INCOME_WEIGHT,
            fulfillment_weight=FULFILLMENT_WEIGHT,
            max_mean_deviation=PEAK_RMSD,
            min_mean_deviation=0,
            min_income=MIN_INCOME,
            max_income=MAX_INCOME,
        )
        return model

    def optimize_multi_step(self, load_timeseries=None, quadratic=False):
        """
        Run multi-step optimization.

        Args:
            load_timeseries: Load timeseries for optimization.
            quadratic: Whether to use quadratic optimization.

        Returns:
            The solved model.
        """
        model = self.build_model(load_timeseries=load_timeseries)
        model = self.solve_model(
            model,
            income_weight=0.01,
            fulfillment_weight=0.99,
            max_mean_deviation=PEAK_RMSD,
            min_mean_deviation=0,
            min_income=MIN_INCOME,
            max_income=MAX_INCOME,
            quadratic=quadratic,
        )
        return model


def create_fake_activity_matrix(schedule):
    """Creates an empty activity matrix in the same format as gleam would use."""
    matrix = [
        {
            "planID": 0,
            "childID": 0,
            "NrOfGenes": 0,
            "resourcePlan": [
                {
                    "resourceID": name_to_id[facility],
                    "powerGeneration": schedule[facility],
                }
                for facility in schedule
            ],
        }
    ]
    return matrix


def solve_model(
    timeframe,
    values,
    step_length,
    income_weight,
    fulfillment_weight,
    max_mean_deviation,
    min_mean_deviation,
    max_income,
    min_income,
    quadratic=False,
    load_timeseries=None,
):
    """Legacy function for backward compatibility."""
    generator = ScheduleGenerator(timeframe=timeframe, step_length=step_length)
    model = generator.build_model(load_timeseries=load_timeseries)
    return generator.solve_model(
        model,
        income_weight=income_weight,
        fulfillment_weight=fulfillment_weight,
        max_mean_deviation=max_mean_deviation,
        min_mean_deviation=min_mean_deviation,
        min_income=min_income,
        max_income=max_income,
        quadratic=quadratic,
    )


def schedule_day(load_ts, start_time: int):
    """
    Schedules the optimization for a single day.

    Args:
        load_ts: Load timeseries data
        start_time: Start time for the optimization window
    """
    generator = ScheduleGenerator(timeframe=96, step_length=15 * 60)
    generator.facility_params["bat"]["input"]["SOC_0"] = 0.5

    model = generator.build_model(load_timeseries=[ts[1] for ts in load_ts])

    start_time_seconds = int(
        datetime.datetime(datetime.datetime.now().year, 1, 1).timestamp()
    )
    electricity_prices = generator.get_electricity_price(
        start_time - start_time_seconds
    )

    # Rebuild model with custom prices
    complete_load = {}
    for ts in load_ts:
        complete_load[ts[0]] = -1 * ts[1]
    target = Target(
        "target",
        time_series=complete_load,
        types=["electricity"],
        electricity_prices=electricity_prices,
        step_length=generator.step_length,
    )
    model.add_device(target)

    return generator.solve_model(
        model,
        income_weight=0.1,
        fulfillment_weight=0.9,
        max_mean_deviation=1,
        min_mean_deviation=1,
        min_income=MIN_INCOME,
        max_income=MAX_INCOME,
        quadratic=True,
    )


def connect_and_schedule(
    timeframe,
    step_length,
    all_results_file,
    result_schedule_file,
    quadratic=False,
    load_ts=None,
    plot=False,
    days=1,
    simpleplot=True,
):
    """
    Connects to the system and schedules the optimization process.

    Args:
        timeframe (int): The number of time steps in the optimization horizon (96 usually)
        step_length (int): The duration of each time step in seconds (15 * 60).
        all_results_file (str): The name of the file to save all optimization results (schedule + target).
        result_schedule_file (str): The name of the file to save the schedule results.
        quadratic (bool, optional): Whether to use quadratic optimization. Defaults to False.
        load_ts (str, optional): The path to the file containing the load timeseries data. Defaults to config path.
        plot (bool, optional): Whether to plot the optimization results. Defaults to False.
        days (int, optional): The number of days to optimize. Defaults to 1.
        simpleplot (bool, optional): Whether to use simple plot visualization. Defaults to True.
    """
    if load_ts is None:
        load_ts = get_path("default_load_file")
    generator = ScheduleGenerator(timeframe=timeframe, step_length=step_length)

    data = load_obj(load_ts)
    times = [dt for dt in data["time"]]
    load_series = data["power"]
    load_timeseries = list(zip(times, load_series))
    results_list = []
    result_handler = utils.result_schedule_handler.ResultScheduleHandler(
        schedule_filename=result_schedule_file
    )
    for i in range(days):
        logger.info(f"Optimizing day {i + 1}/{days}...")
        target = [
            a[1] / 1000000
            for a in list(
                filter(
                    lambda x: x[0] >= i * 96 and x[0] < (i + 1) * 96, load_timeseries
                )
            )
        ]
        logger.debug(f"Target length: {len(target)} timesteps")

        model = generator.optimize_multi_step(
            load_timeseries=target, quadratic=quadratic
        )

        milp_schedule = generator.extract_schedule_from_result(model)
        milp_result = model.get_attribute_by_name(
            "target", "electricity_power"
        ).extract_values()
        milp_result = [-milp_result[t] for t in range(timeframe)]
        logger.debug(f"MILP result length: {len(milp_result)} timesteps")

        logger.debug("Schedule extraction completed")
        combined_schedule = {
            "milp_power": milp_result,
            "milp_schedule": milp_schedule,
        }
        results_list.append((milp_result, target))
        if plot:
            output_config = get_output()
            gleam_file = output_config.get("gleam_curve", "gleam_curve.json")
            with open(gleam_file, "r", encoding="utf-8") as f:
                ems_schedule = json.load(f)
            logger.debug(f"EMS schedule length: {len(ems_schedule)}")
            ems_sched_plot = ems_schedule
            if quadratic:
                mosaik_plotter.plot_mosaik_result_curves(
                    None,
                    combined_schedule["milp_power"],
                    ems_sched_plot[::15],
                    target[:-1],
                    name="mosaik_plot_quadratic.png",
                )
            else:
                mosaik_plotter.plot_mosaik_result_curves(
                    combined_schedule["milp_power"],
                    None,
                    ems_sched_plot[::15],
                    target[:-1],
                    name="mosaik_plot_linear.png",
                )
        if simpleplot:
            output_config = get_output()
            simpleplot_prefix = output_config.get("simpleplot_prefix", "simpleplot")
            generate_plot(
                [milp_result, target],
                ["milp", "target"],
                filename=f"{simpleplot_prefix}_{i}.png",
            )
        with open(all_results_file, "w", encoding="utf-8") as f:
            json.dump(results_list, f)
        if result_schedule_file:
            result_handler.write_day(milp_schedule)


def single_step_optimization(timeframe, values, step_length):
    """Legacy function for backward compatibility."""
    generator = ScheduleGenerator(timeframe=timeframe, step_length=step_length)
    return generator.optimize_single_step()


def multi_step_optimization(
    timeframe, values, step_length, quadratic=False, load_timeseries=None
):
    """Legacy function for backward compatibility."""
    generator = ScheduleGenerator(timeframe=timeframe, step_length=step_length)
    return generator.optimize_multi_step(
        load_timeseries=load_timeseries, quadratic=quadratic
    )
