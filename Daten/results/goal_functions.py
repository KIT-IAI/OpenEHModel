import math
import pickle
#from . import boundary_value_calc

# TODO: Diese Preise sollte es von anderer Stelle geben!
# Hard coded prices are as well hard coded in boundary_value_calc
CH4_to_CO2 = (
    44 / 16
)  # (molar mass CO2)/(molar mass CH4) --> factor for additional weight when oxidating CH4 to Co2
pr_CO2 = -25 / 1000  # €/kg
# ToDo: Preise festlegen und Vorzeichen einmal überprüfen
H2_Gasstation_price_sell = (
    5.59  # €/kg grüner Wassserstoff Quelle: E-bridge Consulting GMBH
)

H2_pipeline_price_buy = (
    H2_Gasstation_price_sell * 5
)  # geschätzter Preis auf Basis von 9,5 €/kg an H2-Tankstelle ??
H2_pipeline_price_sell = 0

# TODO Strafe festlegen
penalty_H2 = 1  # Strafpreis für Bilanzverletzung n H2 Massenbilanz


def load_obj(name):
    with open(name + ".pkl", "rb") as f:
        return pickle.load(f)


#
# def TIM_Meet_Demand(ems_df, systemvalues):
#     """
#     Function that takes the EMS Data Frame and evaluates it in regard to the
#     electric power flow.
#
#     Isn't called -> dead code
#     ...
#
#     Parameters
#     ----------
#     EMS Data Frame
#
#     Return
#     ------
#     returns a Goal Value, that is sent to GLEAM, where it is mapped to a fitness value
#     """
#     time_interval = systemvalues["intervall_time"]  # time step size
#     total_deviation = 0
#
#     ## Test für alternative Berechnung
#     # sum_ehg_el = []
#     # ehg_el = zip(ems_df["Lastreihe"]["Lastreihe"], ems_df["BHKW"]["P_el_BHKW"], ems_df["Electrolyseur"]["P_el"], ems_df["Battery"]["P"])
#     # for prediction, bhkw, electrolyseur, battery in ehg_el:
#     #    sum_ehg_el.append(((prediction - (bhkw + electrolyseur + battery)) / 100_000) ** 2) # Deviation of 10kW
#     # rmse = math.sqrt(sum(sum_ehg_el)/len(ems_df["Lastreihe"]["Lastreihe"]))
#
#     for intervall_step in range(systemvalues["intervall_steps"]):
#         prediction_value = ems_df["Lastreihe"]["P_el"][intervall_step]  # in W
#         sum_electricity = ems_df["BHKW"]["P_el"][intervall_step] + ems_df["Electrolyseur"]["P_el"][intervall_step] \
#                           + ems_df["Battery"]["P"][intervall_step]  # all in W
#         deviation_el = (((prediction_value - sum_electricity) / 1_000_000 / 3600) * time_interval  # make W - > MWh
#                         ) ** 2  # square to make case in-sensitive and weight
#         total_deviation += math.sqrt(deviation_el)  # sum overall single deviations
#         # KB: square root of Tim's MA is included
#     return total_deviation


# def RMSD_function(EMS_df, Systemvalues):
#     """
#     Function that takes the EMS Data Frame and evaluates it in regard to the
#     electric power flow. Root Mean Square Deviation Methode is used in order to calculate deviation between expected
#     real value.
#     Function RMSD: RMSD = sqrt{ sum_t^T[ (Expected_value(t) - real_value(t))^2 ] / T }
#
#     Is called in EMS.py and I think it's returned to GLEAM
#     ...
#
#     Parameters
#     ----------
#     EMS Data Frame
#     Systemvalues
#
#     Return
#     ------
#     returns a Goal Value, that is sent to GLEAM, where it is mapped to a fitness value
#     """
#     SD = 0  # SD = Squared Deviation
#     # fist calculate the quadratic sum over all steps
#     for i in range(Systemvalues["intervall_steps"]):
#         SD = ((-1 * EMS_df["Lastreihe"]["P_el"][i]  # W
#                + EMS_df["BHKW"]["P_el"][i]  # W
#                + EMS_df["Electrolyseur"]["P_el"][i]  # W
#                + EMS_df["Battery"]["P"][i]  # W
#                # + EMS_df["BGP"]["P_el"][i]            # W  Why is BGP commented out?
#                ) / 1_000_000 / 3600 * Systemvalues["intervall_time"]) ** 2 + SD
#     RMSD = math.sqrt(SD / Systemvalues["intervall_steps"])
#     # print("RMSD: ", RMSD)
#     return RMSD


def RMSE_function(EMS_df, Systemvalues, optimierung):
    optimierung += 1
    data = load_obj(
        "/home/ws/unlje/PycharmProjects/ee-hub-mosaik/Analysis/Data/fixed_interval/"
        + str(optimierung)
        + "time_interval_assignment"
    )
    # time_offset = EMS_df["Lastreihe"]["time"][0]
    time_list = []
    for i in range(97):
        time_list.append(i * 900)

    time_list.extend(data["new_time"])
    time_set = set(time_list)
    time_list = list(time_set)
    time_list.sort()
    SD = 0
    for i in range(1, len(time_list)):
        j = time_list[i] // 900
        if j == 96:
            j = 95
        n = 1

        while time_list[i] > data["new_time"][n - 1]:
            n += 1

        # TODO: Abfrage zu Lastreihe P_el == 0, dann SD=0 um Zeiten ohne Lastvorgabe für Netzdienstleistung abzufangen
        if EMS_df["Lastreihe"]["P_el"][j] == 0:
            SD += 0
        else:
            SD += (
                (time_list[i] - time_list[i - 1])
                * (
                    -EMS_df["Lastreihe"]["P_el"][j]
                    + EMS_df["BHKW"]["P_el"][n - 1]
                    + EMS_df["Electrolyseur"]["P_el"][n - 1]
                    + EMS_df["Battery"]["P"][n - 1]
                )
                / 3600
                / 1000000
            ) ** 2

    RMSD = math.sqrt(SD / len(time_list))

    # SD = ((-1 * EMS_df["Lastreihe"]["P_el"][0]  # W
    #                + EMS_df["BHKW"]["P_el"][0]  # W
    #                + EMS_df["Electrolyseur"]["P_el"][0]  # W
    #                + EMS_df["Battery"]["P"][0]  # W
    #                # + EMS_df["BGP"]["P_el"][i]            # W
    #                ) / 1000000 / 3600 * data["new_time"][0]) ** 2     EMS_df["Electrolyseur"]["P_el"]
    # # SD = Squared Deviation
    # # fist calculate the quadratic sum over all steps
    # for i in range(1,len(data["new_time"])):
    #     SD += ((-1* EMS_df["Lastreihe"]["P_el"][i] + EMS_df["BHKW"]["P_el"][i] + EMS_df["Electrolyseur"]["P_el"][i] + EMS_df["Electrolyseur"]["P_el"][i] + EMS_df["Battery"]["P"][i]) / 1000000 / 3600 * (data["new_time"][i]-data["new_time"][i-1])) ** 2
    #
    # RMSD = math.sqrt(SD / len(data["new_time"]))
    # print("RMSD: ", RMSD)
    return RMSD


def CO2(EMS_df, Systemvalues, optimierung):
    """
    Function that takes the EMS Data Frame and evaluates it in regard to the
    CO2 output. Calculates costs for CO2 input/ output. Profit is positive, loss is negative
    ...

    Parameters
    ----------
    EMS Data Frame

    Return
    ------
    returns a Goal Value, that is sent to GLEAM, where it is mapped to a fitness value
    """

    optimierung += 1
    data = load_obj(
        "/home/ws/unlje/PycharmProjects/ee-hub-mosaik/Analysis/Data/fixed_interval/"
        + str(optimierung)
        + "time_interval_assignment"
    )

    CO2 = (
        -EMS_df["BHKW"]["m_CH4"][0] * CH4_to_CO2 + EMS_df["Methanation"]["m_CO2"][0]
    ) * data["new_time"][0]
    for i in range(1, len(data["new_time"])):
        CO2 += (
            -EMS_df["BHKW"]["m_CH4"][i] * CH4_to_CO2 + EMS_df["Methanation"]["m_CO2"][i]
        ) * (data["new_time"][i] - data["new_time"][i - 1])

    cost = CO2 * pr_CO2  # ks * €/kg -> €
    return cost


def Cost(EMS_df, Systemvalues, optimierung):
    """
    Function that takes the EMS Data Frame and evaluates it in regard to the
    total system Cost. Profit is positive, loss is negative.
    ...
    Parameters
    ----------
    EMS Data Frame

    Return
    ------
    returns a Goal Value, that is sent to GLEAM, where it is mapped to a fitness value
    """

    optimierung += 1
    data = load_obj(
        "/home/ws/unlje/PycharmProjects/ee-hub-mosaik/Analysis/Data/fixed_interval/"
        + str(optimierung)
        + "time_interval_assignment"
    )

    time_list = []
    for i in range(96):
        time_list.append(i * 900)

    time_list.extend(data["new_time"])
    time_set = set(time_list)
    time_list = list(time_set)
    time_list.sort()

    cost = 0
    cost_h2 = 0
    cost_heat = 0
    cost_ch4 = 0
    cost_el = 0

    for i in range(1, len(time_list)):
        j = time_list[i] // 900
        if j == 96:
            j = 95
        n = 1

        while time_list[i] > data["new_time"][n]:
            n += 1

        cost_el += (
            (time_list[i] - time_list[i - 1])
            * (
                EMS_df["BHKW"]["P_el"][n - 1]
                + EMS_df["Electrolyseur"]["P_el"][n - 1]
                + EMS_df["Battery"]["P"][n - 1]
            )
            / 3600
            / 1_000_000
        ) * EMS_df["Electricitygrid"]["price"][j]
        cost_ch4 += (
            (time_list[i] - time_list[i - 1])
            * (
                (EMS_df["Methanation"]["m_CH4"][n - 1] * 55.5 * 1_000_000)
                + (EMS_df["BHKW"]["m_CH4"][n - 1] * 55.5 * 1_000_000)
                + (EMS_df["Gasstorage"]["P"][n - 1] * 39.8 * 1_000_000)
            )
            / 3600
            / 1_000
        ) * EMS_df["Gasgrid"]["gas_demand_price_kwh"][j]
        cost_heat += (
            (time_list[i] - time_list[i - 1])
            * (EMS_df["BHKW"]["Q"][n - 1] + EMS_df["Methanation"]["Q"][n - 1])
            / 3600
            / 1_000
        ) * EMS_df["Gasgrid"]["gas_demand_price_kwh"][j]

        Sum_H2 = (
            EMS_df["Electrolyseur"]["m_H2"][n - 1]
            + EMS_df["Methanation"]["m_H2"][n - 1]
        )
        if Sum_H2 <= 0:
            Price_H2 = Sum_H2 * H2_pipeline_price_buy
        else:
            Price_H2 = Sum_H2 * H2_Gasstation_price_sell

        cost_h2 += (time_list[i] - time_list[i - 1]) * Price_H2
    cost = cost_el + cost_ch4 + cost_heat + cost_h2
    return cost


# calculates to what extent goal values fulfill boundary values
# muss dann aufgerufen werden, wenn ich die sonstigen Kosten berechne
def degree_of_fulfillment(EMS_df, Systemvalues, simulation_parameters, optimierung):
    # set parameters
    start_time = float(
        Systemvalues["start_time"]
    )  # current time starts at 900s equal to 15 mins | works
    stop_time = (
        Systemvalues["stop_time"] + 900
    )  # stop time of currently simulated day in s, +900 equals + one step ->
    # as many steps as in Cost()

    soc_gasstorage = simulation_parameters["Gasstorage"]["output"][
        "SOC_Gasstorage"
    ]  # works
    soc_battery = simulation_parameters["Battery"]["output"]["SOC"]  # works

    # calculate simulated cost and boundary values
    simulated_cost = Cost(EMS_df, Systemvalues, optimierung) + CO2(
        EMS_df, Systemvalues, optimierung
    )  # works
    boundary_values_cost = boundary_value_calc.sum_cost_boundaries(
        start_time, stop_time, soc_battery, soc_gasstorage
    )

    boundary_profit = boundary_values_cost[0]
    boundary_loss = boundary_values_cost[1]

    """
    print("simulated_cost", simulated_cost)
    print("boundary_profit", boundary_profit)
    print("boundary_loss", boundary_loss)
    """

    # positive = profit, negative = loss

    # muss ich sonderfälle betrachten, in denen boundary_loss > 0 und boundary profit < 0 ist ?
    # oder den sonderfall, dass beide boundary values = 0 sind?

    # calculate degree of fulfillment
    d_o_fulfillment = (simulated_cost - boundary_loss) / (
        boundary_profit - boundary_loss
    )
    #  print(f"{d_o_fulfillment}")
    # ich habe die vorzeichen jetzt ein mal genau umgedreht. Noch mal auf dem Papier überprüfen!

    #  print("d_o_fulfillment:", d_o_fulfillment)

    # intercept values outside the limits
    """
    if d_o_fulfillment > 1:
        d_o_fulfillment = 1
    if d_o_fulfillment < 0:
        d_o_fulfillment = 0
    """

    return d_o_fulfillment, boundary_profit, boundary_loss


def debug_dof(EMS_df, Systemvalues, simulation_parameters):
    # set parameters
    start_time = float(
        Systemvalues["start_time"]
    )  # current time starts at 900s equal to 15 mins | works
    stop_time = (
        Systemvalues["stop_time"] + 900
    )  # stop time of currently simulated day in s +900 equals + one step ->
    # as many steps as in Cost()

    soc_gasstorage = simulation_parameters["Gasstorage"]["output"][
        "SOC_Gasstorage"
    ]  # works
    soc_battery = simulation_parameters["Battery"]["output"]["SOC"]  # works

    # for debugging: Print costs of every plant for every day
    cost_chp = 0
    cost_meth = 0
    cost_pem = 0
    cost_bat = 0
    cost_gasstorage = 0
    cost_total = 0
    cost_h2 = 0
    Price_H2 = 0

    for i in range(
        Systemvalues["intervall_steps"]
    ):  # 96 intervall steps, 24hrs with one step each 15 mins
        time = Systemvalues["intervall_time"]  # 900[s] equals 15 mins

        # cost for electricity
        cost_chp += (
            EMS_df["BHKW"]["P_el"][i]
            / 1000000
            * time
            / 3600
            * EMS_df["Electricitygrid"]["price"][i]
        )  # W -> MWh. MWh * €/MWh -> €
        cost_bat += (
            EMS_df["Battery"]["P"][i]
            / 1000000
            * time
            / 3600
            * EMS_df["Electricitygrid"]["price"][i]
        )  # W -> MWh. MWh * €/MWh -> €
        cost_pem += (
            EMS_df["Electrolyseur"]["P_el"][i]
            / 1000000
            * time
            / 3600
            * EMS_df["Electricitygrid"]["price"][i]
        )  # W -> MWh. MWh * €/MWh -> €

        # cost for gas
        cost_meth += (
            EMS_df["Methanation"]["m_CH4"][i]
            * 55.5
            * 1000000
            / 1000
            / 3600
            * time
            * EMS_df["Gasgrid"]["gas_demand_price_kwh"][i]
        )  # kg/s -> W, W -> kWh, kWh * €/kWh -> €
        cost_chp += (
            EMS_df["BHKW"]["m_CH4"][i]
            * 55.5
            * 1000000
            / 1000
            / 3600
            * time
            * EMS_df["Gasgrid"]["gas_demand_price_kwh"][i]
        )  # kg/s -> W, W -> kWh, kWh * €/kWh -> €
        cost_gasstorage += (
            EMS_df["Gasstorage"]["P"][i]
            * 39.8
            * 1000000
            / 1000
            / 3600
            * time
            * EMS_df["Gasgrid"]["gas_demand_price_kwh"][i]
        )  # m³/s -> W, W -> kWh, kWh * €/kWh -> €

        # cost for heat
        cost_meth += (
            EMS_df["Methanation"]["Q"][i]
            / 1000
            / 3600
            * time
            * EMS_df["Gasgrid"]["gas_demand_price_kwh"][i]
        )  # W -> kWh, kWh * €/kWh -> €
        cost_chp += (
            EMS_df["BHKW"]["Q"][i]
            / 1000
            / 3600
            * time
            * EMS_df["Gasgrid"]["gas_demand_price_kwh"][i]
        )  # W -> kWh, kWh * €/kWh -> €

        # cost for CO2
        cost_chp -= (
            EMS_df["BHKW"]["m_CH4"][i] * CH4_to_CO2 * time * pr_CO2
        )  # kg/s * s * €/kg -> €
        cost_meth += (
            EMS_df["Methanation"]["m_CO2"][i] * time * pr_CO2
        )  # kg/s * s * €/kg -> €

        # cost for hydrogen
        """
        cost_pem += EMS_df["Electrolyseur"]["m_H2"][i] * H2_Gasstation_price_sell
        cost_meth += EMS_df["Methanation"]["m_H2"][i] * H2_Gasstation_price_sell

        my_cost_h2 = (EMS_df["Electrolyseur"]["m_H2"][i] + EMS_df["Methanation"]["m_H2"][i])* H2_Gasstation_price_sell
        """

        # H2
        Sum_H2 = (
            EMS_df["Electrolyseur"]["m_H2"][i] + EMS_df["Methanation"]["m_H2"][i]
        )  # + EMS_df['Gasstation']['P'][i]

        # Vorzeichen ist gechecked
        if Sum_H2 <= 0:
            Price_H2 += Sum_H2 * H2_pipeline_price_buy
        else:
            Price_H2 += Sum_H2 * H2_Gasstation_price_sell

        cost_meth_pem = cost_pem + cost_meth + (Price_H2 * time)

    cost_total = cost_pem + cost_gasstorage + cost_bat + cost_meth + cost_chp + cost_h2
    """
    print(f"costs in goal_functions: bat: {cost_bat}, gasstorage: {cost_gasstorage}"
          f" chp: {cost_chp}, methanation: {cost_meth}, pem: {cost_pem}")
    print(f"sum of costs over all plants: {cost_total}")
    #  print(f"cost_h: {cost_h2}, wheras my cost h2 = {my_cost_h2}")
    print("Abweichungen wegen unterschiedlicher hydrogen berechnung")
    """

    # calculate boundary values
    start = int(start_time / 60 / 15)  # start time in 15 minute intervals
    stop = int(stop_time / 60 / 15)  # stop time in 15 minute intervals
    timeinterval = 900  # [s] datapoint every 900 s equals 15 mins
    steps_per_calc = stop - start

    El_grid_PATH = "/home/ws/unlje/PycharmProjects/ee-hub-mosaik/EMS/library/Daten/"
    Electricity_grid = load_obj(El_grid_PATH + "electricity_grid_04-11_04_2022")

    # Gas (Methane)
    gas_grid_path = "../EMS/library/Daten/Gasdemand_test"
    gas_grid = load_obj(gas_grid_path)  # [€/kwh] lt. goal_functions.py
    gas_grid_price = []
    for i in range(len(gas_grid["Price"]) * 4):  # create one datapoint every 15 mins
        gas_grid_price.append(gas_grid["Price"][i // 4])

    # slicing resources, which are called in boundary value calculation of the single plants
    slice_el = Electricity_grid["price"][start:stop]
    slice_gas = gas_grid_price[start:stop]
    slice_heat = slice_gas  # heat and gas price are currently the same

    boundary_values_battery = boundary_value_calc.calc_cost_battery_newest(
        steps_per_calc, timeinterval, soc_battery, slice_el
    )

    boundary_values_chp = boundary_value_calc.calc_boundary_values_chp(
        steps_per_calc, timeinterval, slice_gas, slice_el, slice_heat, pr_CO2
    )

    boundary_values_gasstorage = boundary_value_calc.calc_cost_gasstorage(
        steps_per_calc, timeinterval, soc_gasstorage, slice_gas
    )

    boundary_values_pem = boundary_value_calc.calc_boundary_values_pem(
        steps_per_calc, timeinterval, slice_el
    )
    boundary_values_meth = boundary_value_calc.calc_boundary_values_methanation(
        steps_per_calc,
        timeinterval,
        H2_pipeline_price_buy,
        pr_CO2,
        slice_gas,
        slice_heat,
    )

    bound_profit_pem_meth = boundary_values_pem[0] + boundary_values_meth[0]

    costs = {
        "battery_simulated": cost_bat,
        "battery_profit": boundary_values_battery[0],
        "chp_simulated": cost_chp,
        "chp_profit": boundary_values_chp[0],
        "gasstorage_simulated": cost_gasstorage,
        "gasstorage_profit": boundary_values_gasstorage[0],
        "pem_meth_simulated": cost_meth_pem,
        "pem_meth_profit": bound_profit_pem_meth,
    }

    return costs


def dof_RMSD(EMS_df, Systemvalues, optimierung):
    """
    Calculates the degree of fulfillment of RMSD

    Returns
    -------
    dof_RMSD: degree of fulfillment of RMSD
    RMSD_min: Minimum RMSD boundary value
    RMSD_max: Maximum RMSD boundary value
    """

    RMSD_min = boundary_value_calc.calc_RMSD_boundaries(EMS_df, Systemvalues)[0]
    RMSD_max = boundary_value_calc.calc_RMSD_boundaries(EMS_df, Systemvalues)[1]

    simulated_RMSD = RMSE_function(EMS_df, Systemvalues, optimierung)

    dof_RMSD = (simulated_RMSD - RMSD_min) / (RMSD_max - RMSD_min)

    return dof_RMSD, RMSD_min, RMSD_max


def H2_Line(EMS_df, Systemvalues, optimierung):
    """
    Function that takes the EMS Data Frame and evaluates it in regard to the
    total system Cost.
    Is currently commented out
    ...

    Parameters
    ----------
    EMS Data Frame

    Return
    ------
    returns a Goal Value, that is sent to GLEAM, where it is mapped to a fitness value
    """
    optimierung += 1
    data = load_obj(
        "/home/ws/rt7283/PycharmProjects/ee-hub-mosaik/Analysis/Data/fixed_interval/"
        + str(optimierung)
        + "time_interval_assignment"
    )

    bilanz_H2 = 0

    bilanz_H2 = (
        EMS_df["Methanation"]["m_H2"][0]  # kg/s
        + EMS_df["Gasstation"]["P"][0]  # kg/s
        + EMS_df["Electrolyseur"]["m_H2"][0]
    ) * data["new_time"][
        0
    ]  # kg/s
    for i in range(1, len(data["new_time"])):
        # Elektisch:
        bilanz_H2 = bilanz_H2 + (
            EMS_df["Methanation"]["m_H2"][i]  # kg/s
            + EMS_df["Gasstation"]["P"][i]  # kg/s
            + EMS_df["Electrolyseur"]["m_H2"][i]
        ) * (
            data["new_time"][i] - data["new_time"][i - 1]
        )  # kg/s
    bilanz_H2 = bilanz_H2 * penalty_H2
    return bilanz_H2
