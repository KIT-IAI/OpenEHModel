import pickle
import numpy as np
from pyomo.opt import SolverFactory

from components.target import Target
from components.grid import Grid
from load_import import load_obj
from indexed_model import IndexedModel
from components.converter import Converter
from components.storage import Storage
from redis_utils import *
from Daten.results.plotter import plot_load_comparison

facility_names = [
    "chp",
    "Electrolyseur",
    "Battery",
    "methanization",
]
name_to_id = {
    "chp": "1",
    "Electrolyseur": "2",
    "Battery": "3",
    "Gasstorage": "4",
    "methanization": "6",
    "Lastreihe": "10",
}

# Specific energy of methane mwhH/kg
METHANE_ENERGY = 15.4 / 1000
# Specific energy of hydrogen mwH/kg
H2_ENERGY = 0.039389

# Weights for the optimization
INCOME_WEIGHT = 0.4
FULFILLMENT_WEIGHT = 0.6

# Cost for CO2 in €/kg (certificates from 2021)
pr_CO2 = 25 / 1000
# Conversion factor from CH4 to CO2
CH4_to_CO2 = (44 / 16) * (1 / METHANE_ENERGY)

# Values from the evaluation.csv
PEAK_RMSD = 1.0693029029
MIN_INCOME = -26875.717205459492
MAX_INCOME = 7954.206175268439


def get_gas_price(timeframe, step_length):
    data = load_obj("Daten/Gasdemand_test.pkl")
    times = data["time"]
    prices = data["Price"]
    result = []
    prev_time = 0
    for time, price in zip(times, prices):
        while prev_time < time and prev_time < timeframe * step_length:
            result.append(price * 1000) # €/kwh to €/mwH
            prev_time += step_length
        if prev_time > timeframe * step_length:
            break
    return result


def get_electricity_price(timeframe, step_length):
    data = load_obj("Daten/electricity_grid_04-11_04_2022.pkl")
    times = data["time"]
    prices = data["price"]
    result = []
    prev_time = 0
    for time, price in zip(times, prices):
        while prev_time < time and prev_time < timeframe * step_length:
            result.append(price * 10) # cent/kwH to €/mwH
            prev_time += step_length
        if prev_time > timeframe * step_length:
            break
    return result


def model_from_facility_parameters(parameters, timeframe, step_length):
    """
    parameters: systemvalues from simulation
    timeframe: number of steps to be simulated (needs to be the same in EMS)
    step_length: length of a time step in seconds (also currently the same as in EMS)
    """
    model = IndexedModel(index=range(0, timeframe))

    heat_price = get_gas_price(timeframe, step_length)
    print("initiated models")
    chp_params = parameters["parameters"]["BHKW"]["metadata"]
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
        step_length=step_length,
    )
    model.add_device(chp)

    electrolysis_params = parameters["parameters"]["Electrolyseur"]
    electrolysis = Converter(
        name="Electrolyseur",
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
        step_length=step_length,
    )
    model.add_device(electrolysis)

    methanization_params = parameters["parameters"]["Methanation"]
    methanization = Converter(
        name="methanization",
        max_powers={"methane": (methanization_params["input"]["P_max_meth"]) / 1000000},
        min_powers={"methane": methanization_params["input"]["P_min_meth"] / 1000000},
        input_types=["h2"],
        output_types=["methane"],
        ramp_up=methanization_params["input"]["t_ramp_meth"],
        ramp_down=1,
        pr_CO2=pr_CO2,
        CH4_to_CO2=CH4_to_CO2,
        conversion_factors={
            "methane": 1,
            "h2": 0.25 * H2_ENERGY * 62.3 * (1 / METHANE_ENERGY) * (1 / 496),
        },  # mol * mwh/kg * kg/mol * kg/mwH * mol/kg
        step_length=step_length,
    )
    # 62.3 kg/mol methane
    # 496 kg/mol h2
    model.add_device(methanization)
    print("added converters")

    h2_storage = Storage(
        name="h2_storage",
        max_charging_power=1,
        max_discharging_power=2,
        capacity=10,
        input_types=["h2"],
        charging_efficiency=1,
        step_length=step_length,
        initial_charge=0,
    )
    model.add_device(h2_storage)

    battery_params = parameters["parameters"]["Battery"]["input"]
    battery = Storage(
        name="Battery",
        max_charging_power=battery_params["P_max_Bat"] / 1000000,
        max_discharging_power=battery_params["P_max_Bat"] / 1000000,
        capacity=battery_params["EBat"] / 3600000000, # Joule to mwh
        initial_charge=battery_params["EBat"] / 3600000000 / 2,
        charging_efficiency=battery_params["eta_Bat"],
        input_types=["electricity"],
        step_length=step_length,
    )
    model.add_device(battery)

    gas_storage = Storage(
        name="Gasstorage",
        max_charging_power=0.27 * METHANE_ENERGY * step_length,
        max_discharging_power=0.27 * METHANE_ENERGY * step_length,
        capacity=1500 * METHANE_ENERGY,
        initial_charge=750 * METHANE_ENERGY,
        charging_efficiency=1,
        input_types=["methane"],
        step_length=step_length,
    )
    model.add_device(gas_storage)
    print("added storage")
    return model


def add_prices_to_model(model, timeframe, step_length):
    """
     Reads data from the grid files to get
     energy prices for the Model
    """
    gas_price = get_gas_price(timeframe, step_length)
    gas_network = Grid(
        "gas_grid",
        max_buying_power=-1000,
        max_selling_power=1000,
        energy_cost={"methane": gas_price},
        types=["methane"],
        step_length=step_length,
    )
    model.add_device(gas_network)
    h2_price = [5.95 / H2_ENERGY for _ in range(timeframe)]
    h2_network = Grid(
        "h2grid",
        max_buying_power=-1000,
        max_selling_power=0,
        energy_cost={"h2": h2_price},
        types=["h2"],
        step_length=step_length,
    )
    model.add_device(h2_network)
    return model


def add_target_to_model(model, timeframe, step_length):
    """
    Reads the demand file to get the target for the energy hub
    """
    data = load_obj("Daten/Lastreihe_CN_04-11_04_2022.pkl")
    times = data["time"][1:]
    load_series = data["Lastreihe"][1:]
    result = []
    for time,  load in zip(times, load_series):
        if time > timeframe * step_length:
            break
        result.append(-load / 1000000)
    electricity_prices = get_electricity_price(timeframe, step_length)

    target = Target(
        "target",
        time_series=result,
        types=["electricity"],
        electricity_prices=electricity_prices,
        step_length=step_length,
    )
    model.add_device(target)
    return model


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
):
    """

    :param timeframe: Number of steps
    :param values: Systemvalues to use
    :param step_length Number of seconds per step
    """
    print("received values")
    model = model_from_facility_parameters(values, timeframe, step_length)
    print("generated facilities")
    model = add_prices_to_model(model, timeframe, step_length)
    print("added prices")
    model = add_target_to_model(model, timeframe, step_length)
    print("added target")
    model.set_objective_with_weights(
        income_weight=income_weight,
        fulfillment_weight=fulfillment_weight,
        step_length=step_length,
        max_mean_deviation=max_mean_deviation,
        min_mean_deviation=min_mean_deviation,
        min_income=min_income,
        max_income=max_income,
    )
    print("objective created")
    model.generate_power_balance()
    print("power balance created")
    gurobi = SolverFactory("gurobi", solver_io="python")
    print("starting to solve")
    result = gurobi.solve(model, report_timing=True)
    print(result)

    print("income dof, sum (€)", model.income_dof(), model.income_sum())
    print(
        "target dof mean squared",
        model.fulfillment_dof(),
        "| sum (mean_deviation, mwH^2)",
        model.mean_deviation(),
    )
    return model


def extract_schedule_from_result(model):
    schedule = {}
    for facility in facility_names:
        if facility == "Battery":
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


def create_fake_activity_matrix(schedule):
    """
    Creates an empty activity matrix in the same format as gleam would use (to send to the EMS)
    """
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


def connect_and_schedule(timeframe, step_length, filename):
    data = load_obj("Daten/Lastreihe_CN_04-11_04_2022.pkl")
    times = data["time"]
    load_series = data["Lastreihe"]
    target = []
    for time, load in zip(times, load_series):
        if time > timeframe * 900:
            break
        target.append(load / 1000000)

    redis, system = engage_redis(cluster=False, channel="Systemvalues")
    values = wait_for_stream(system)
    print(values)

    model = multi_step_optimization(timeframe, values, step_length)

    milp_schedule = extract_schedule_from_result(model)
    matrix = create_fake_activity_matrix(milp_schedule)

    send_redis(matrix, redis)
    milp_result = model.get_attribute_by_name(
        "target", "electricity_power"
    ).extract_values()
    milp_result = [-milp_result[t] for t in range(timeframe)]
    redis, r_schedule = engage_redis(cluster=False, channel="Schedule")
    ems_schedule = wait_for_stream(r_schedule)
    print("got schedule")
    combined_schedule = {
        "milp_power": milp_result,
        "milp_schedule": milp_schedule,
        "ems": ems_schedule,

    }
    with open("Daten/results/" + filename, "w") as f:
        json.dump(combined_schedule, f)

    plot_load_comparison(milp=milp_result, milp_ems=ems_schedule, systemvalues=values)
    model_values = model.values()


def single_step_optimization(timeframe, values, target):
    model = solve_model(
        timeframe,
        values,
        900,
        income_weight=INCOME_WEIGHT,
        fulfillment_weight=FULFILLMENT_WEIGHT,
        max_mean_deviation=PEAK_RMSD,
        min_mean_deviation=0,
        min_income=MIN_INCOME,
        max_income=MAX_INCOME,
    )
    return model


def multi_step_optimization(timeframe, values, step_length):
    """
    Test if better performance possible when using own prediction for optimal incomes and deviation
    """
    model = solve_model(
        timeframe,
        values,
        step_length,
        income_weight=0,
        fulfillment_weight=1,
        max_mean_deviation=PEAK_RMSD,
        min_mean_deviation=0,
        min_income=MIN_INCOME,
        max_income=MAX_INCOME,
    )
    minimum_income_result = model.income_sum()
    min_mean_deviation = model.mean_deviation()
    print("min_mean_deviation", min_mean_deviation)
    print("min_income", minimum_income_result)
    model = solve_model(
        timeframe,
        values,
        step_length,
        income_weight=1,
        fulfillment_weight=0,
        max_mean_deviation=PEAK_RMSD,
        min_mean_deviation=min_mean_deviation,
        min_income=MIN_INCOME,
        max_income=MAX_INCOME,
    )
    max_income_result = model.income_sum()
    max_mean_deviation = model.mean_deviation()
    print("optimum_income", max_income_result)
    print("peak_deviation", max_mean_deviation)
    model = solve_model(
        timeframe,
        values,
        step_length,
        income_weight=INCOME_WEIGHT,
        fulfillment_weight=FULFILLMENT_WEIGHT,
        max_mean_deviation=max_mean_deviation,
        min_mean_deviation=min_mean_deviation,
        min_income=minimum_income_result,
        max_income=max_income_result,
    )
    return model
