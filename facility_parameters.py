import json
from os import path as os_path
dirname = os_path.dirname(__file__)
from sys import path
path.append(os_path.join(os_path.dirname(__file__), '../'))
from json import dumps

"""
Example_dict = {
    "input": {
        any inputs that the FMU can use as input. NO ADDITIONAL "inputs" allowed!!!
    },
    "output": {
        any outputs that the FMU has implemented. NO ADDITIONAL "output" allowed
    },
    "metadata": {
        needs: fmu_directory
        if this model shall be used in the EMS for optimization, the dictionary
        EMS: {
            supported entries can be found in the EMS. (e.g. P_max, P_min, type, opt_range,...)
        }
    }
"""
facility_dict = {}

h2_gasstation_parameters = {
    "input": {
        # parameters for running the FMU:
        "loading_time":  7*24*3600,         # time between deliviery [s]
        "offset_time": 2.5 * 24 * 3600,     # time since last delivery at start of fmu [s]
        "V_h2_tank": 5,                     # tank volume [m3]
        "p_last_h2_tank": 7e5,              # pressure h2 tank last run [Pa]
        "p_min_h2_tank": 1e5,               # "pressure new h2 tank [Pa] "; war vorher 3e5
        "p_max_h2_tank": 300e5,             # max pressure h2 tank [Pa]
        "p_h2_grid": 10e5,                  # "pressure h2 grid [Pa] (input to model)";
        "p_min_h2_grid": 3e5,               # "min pressure h2 grid [Pa] ";
        "p_max_h2_grid": 30e5,              # "max pressure h2 grid [Pa] ";
        "m_h2_max": 0.0005,                 # "mass flow into h2 tank [kg/s] ";
        "X_h2_set": 0.95                    # "mass flow into h2 tank [kg/s] "; Ich denke eher setpoint [0,1] anteilig zu m_h2_max
    },
    "output": {
        # Output parameters:
        "m_h2_int": 0,                 # state of Charge h2 tank [kg] ?
        "m_h2": 0,                     # massflow into h2 tank [kg/s] ?
        "pressure_h2": 0                    # presure of h2 tank [Pa]
    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, '../Modelle/H2_Tankstelle/MGRID_0ch_FMU_H2_0usecases_H2_0delivery_02021_006_030.fmu'),
        "name": "Gasstation",
        "EMS": {
            "eta": 1,
            "E_max": 300e5 * 5 * 2.01588/1000 * 1/(8.31446261815324 * 293.15),
            # in mass with ideal gas law: m = pVM/(RT)
            # p = 300e5 [Pa] = 200e5 [kg*m⁻¹*s⁻²]
            # V = 5 [m^3]
            # M = 2.01588/1000 [kg/mol]
            # R = 8.31446261815324 [kg*m²s⁻²*K⁻¹*mol⁻¹]
            # T = 20 [°C} = 293.15 [K]
            "E_0": 7e5 * 5 * 2.01588/1000 * 1/(8.31446261815324 * 293.15),
            "P_max": 0.0005,
            "name": "Gasstation",
            "Opt_Range": [0, 1],
            "steering": True,
            "Outputs": ["E", "P"],
            "type": "Storage"
        }
    }
}
facility_dict[h2_gasstation_parameters["metadata"]["name"]] = h2_gasstation_parameters

h2_pipeline_parameters = {
    "input": {
        # parameters for running the FMU:
        "V_h2_tank": 5.7*1_000_000_000,  # tank volume [m³]
        "p_last_h2_tank": 2000000,  # pressure h2 tank last run [Pa]
        "m_h2": 0.00  # mass flow  into tank [kg/s]
    },
    "output": {
        # Output parameters:
        "pressure_h2_tank": 100000  # pressure h2 tank [Pa]
    },
    "metadata": {
        "name": "Gasgrid",
        "fmu_directory": os_path.join(dirname, "../Modelle/h2_tank/MGRID_0ch_FMU_H2_0tank_H2_0tank_02021_005_021.fmu")
    }
}
facility_dict[h2_pipeline_parameters["metadata"]["name"]] = h2_pipeline_parameters


bhkw_parameters = {
    "input": {
        "X_set_BHKW": 0,                # "Set point partial load [0,1]";
        "P_BHKW_last": 0,               # "Partial load last run [0,1]";
    },
    "output": {
        "P_BHKW": 0,                    # "El. power output  [W]";
        "Q_BHKW": 0,                    # "Heat output  [W]";
        "m_CH4_BHKW": 0,                # "mass flow methane into BHKW [kg/s]";
        "m_CO2_BHKW": 0,                # "mass flow CO2 out of BHKW [kg/s]";
    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, "../Modelle/MGRID_FMU_BHKW_Environment_0BHKW_02021_011_018.fmu"),
        "P_max_KWK": 2_026_000,           # "Nominal Power KWK";
        "P_min_KWK": 0.35 * 2_026_000,    # W
        "t_startup": 120,                   # " Startup time [s]";
        "Eta_therm_KWK": 0.423,             #  "Thermischer Wirkungsgrad KWK Anlage";
        "name": "BHKW",
        "EMS": {
            "P_min": 709100,
            "P_max": 2026000,
            "Ramp_Rate": 5909,
            "LUT": os_path.join(os_path.dirname(__file__), '../EMS/library/LUT/BHKW.mat'),
            "name": "BHKW",
            "Opt_Range": [0, 1],
            "steering": True,
            "Outputs": ["m_CH4", "P_el", "Q"],
            "type": "Converter"
        }
    }
}
facility_dict[bhkw_parameters["metadata"]["name"]] = bhkw_parameters




bgp_parameters = {
    "input": {

    },
    "output": {
        "m_CH4_BG": 0,
        "m_CO2_BG": 0,
        "P_inject_BG": 0
    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, "../Modelle/FMU_Biogas_Environment_0Biogas_02020_012.fmu"),
        "name": "BGP",
        "EMS": {
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/LUT/BGP_prediction'),
            "name": "BGP",
            "steering": False,
            "Outputs": ["time", "m_CH4", "m_CO2", "P_el"],
            "type": "Prediction"
        }
    }
}
facility_dict[bgp_parameters["metadata"]["name"]] = bgp_parameters


battery_parameters = {
    "input": {
        "X_set_Bat": 0,                 # "Set point partial load [-1,1]";?
        "SOC_0": 0.5,                   # "State-of-charge at start";
        "P_max_Bat": 1_000_000,         #  "Max Power (Charge, Discharge) Battery [W] ";
        "EBat": 10_800_000_000,         # "Capacity Battery [J] ";
        "eta_Bat": 0.93                 # efficiency of Battery [0,1]
    },
    "output": {
        "P_Bat": 0,                     # "El. power flow  [W]";
        "SOC": 0                        # "State of charge [-]";
    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, "../Modelle/MGRID_02206_FMU_Battery_02022_012_014.fmu"),
        "name": "Battery",
        "EMS": {
            "eta": 0.93,
            "E_max": 10800000000,
            "E_0": 10800000000/2,
            "P_max": 1000000,
            "name": "Battery",
            "Opt_Range": [-1, 1],
            "steering": True,
            "Outputs": ["E", "P"],
            "type": "Storage"
        }
    }
}
facility_dict[battery_parameters["metadata"]["name"]] = battery_parameters


methanation_parameters = {
    "input": {
        "p_ch4_tank": 12e5,                  #"pressure CH4  after methanation [Pa]";
        # Relevante Input Parameter:
        "pressure_min_ch4": 0,               #"Minimum CH4  pressure after methanation [Pa]";
        "pressure_max_ch4": 25e5,            #"Minimum CH4  pressure after methanation [Pa]";
        #Abschaltung, wenn Druck im vorgelagerten Wasserstoffspeicher zu gering. Input Parameter:
        "p_h2_tank": 15e5,                   #"pressure hydrogen at methanation input [Pa]";
        #Relevante Parameter:
        "pressure_min_h2": 5e5,             #"Minimum H2 Pressure for methanation [Pa]"; # war vorher 10e5
        "pressure_max_h2": 30e5,             #"Minimum H2 Pressure for methanation [Pa]";
        #3.Für den Start eines steps braucht die FMU den Lastpunkt aus dem letzten run:
        "P_last_meth": 2e5,                  #"Partial load last run [W]";
        #4. … und den Setpunkt: (siehe Frage oben:[0, 1] oder[W]
        "X_set_meth": 0.8,                   #"Set point partial load 1 = 100%";
        #5. Die Dynamik wird abgebildet über die Zeit, die benötigt wird um von 0 auf 100 % anzufahren:
        "t_ramp_meth": 60,                    #"Start-up time from stand-by 0->100% [s]";
        "P_max_meth": 1000000,                # Maximum Power output from Methane(????)
        "P_min_meth": 310000
    },
#Output Parameter:
    "output": {
        "m_ch4_meth": 0,                    #"mass flow out of methanation [kg/s]";
        "m_h2_meth": 0,                     #"mass flow into methanation [kg/s]";
        "m_co2_meth": 0,                    #"mass flow into methanation [kg/s]";
        "P_meth": 0,                        #"Chem. power output (H_s = 55.5e6 J/kg) [W]";
        "Q_meth": 0,                         #"Thermal. power output [W]";

    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, '../Modelle/methanation/MGRID_FMU_Methanation_Environment_0Methanation_02021_005_020.fmu'),
        "name": "Methanation",
        "EMS": {
            "P_min": 310000,
            "P_max": 1000000,
            "Ramp_Rate": 5166,
            "LUT": os_path.join(os_path.dirname(__file__), '../EMS/library/LUT/Methanation_new.mat'),
            "name": "Methanation",
            "Opt_Range": [0, 1],
            "steering": True,
            "Outputs": ['m_CH4', 'm_H2', 'm_CO2', 'P', 'Q'],
            "type": "Converter"
        }
    }
}
facility_dict[methanation_parameters["metadata"]["name"]] = methanation_parameters


pem_parameters = {
    "input": {
        # parameters for initialization:
        "Eta_PEM": 0.73,                # Elektrischer Wirkungsgrad der EL
        "P_max_PEM": 1000000,           # Nominal power electrolysis (el. input) [W]
        "P_min_PEM": 0.31 * 1000000,    # Minimal power electrolysis (el. input) [W]

        # Parameters for active simulation:
        # Abschaltung, wenn Duck im nachgeschalteten Wasserstoffspeicher zu hoch.
        # Input Parameter:
        "p_h2_tank": 1500000,           # pressure hydrogen at methanation input [Pa]
        "pressure_min_h2": 0,           # Minimum H2 Pressure for methanation 1000000 [Pa]
        "pressure_max_h2": 7000000,     # Minimum H2 Pressure for methanation [Pa]

        # für den Start eines steps braucht die FMU den Lastpunkt aus dem letzten run:
        "P_last_PEM": 200000,           # Partial load last run [W]"

        # … und den Setpunkt: (siehe Frage oben: [0,1] oder [W]
        "X_set_PEM": 0.8,               # Set point partial load 1 = 100%"

        # Die Dynamik wird abgebildet über die Zeit, die benötigt wird um von 0 auf 100% anzufahren:
        "t_ramp_PEM": 60                # Start-up time from stand-by 0->100% [s]"
    },
    "output": {
        # Output parameters:
        "m_H2_EL": 0.0,                 # Mass flow into methanation [kg/s]"
        "P_EL": 0.0                     # chem. power output (H_s = 55.5e6 J/kg) [W]"
    },
    "metadata": {
        "fmu_directory": os_path.join(dirname, '../Modelle/pem/MGRID_0ch_FMU_PEM_Environment_0Electrolysis_02021_006_002.fmu'),
        "name": "Electrolyseur",
        "EMS": {
            "P_min": 310000,
            "P_max": 1000000,
            "RampRate": 5166,
            "LUT": os_path.join(os_path.dirname(__file__), '../EMS/library/LUT/PEM.mat'),
            "name": "Electrolyseur",
            "Opt_Range": [0, 1],
            "steering": True,
            "Outputs": ["P_el", "m_H2"],
            "type": "Converter"
        }
    }
}
facility_dict[pem_parameters["metadata"]["name"]] = pem_parameters


usecase_parameters = {
    "input": {
        # parameters for initialization:
        # Parameters for active simulation:
        # Input Parameter:
        "PWin": 10_000_000,                        # 2,5 MW Nennleistung
        "A_PV": 25_000,                          # 25000 m² => 2,5 MW Nennleistung ( ~1kW / m²)
    },
    "output": {
        # Output parameters:
        "P_PV": 0.0,                            # electrical local power generation by PV in [W]
        "P_el_demand": 0.0,                     # local electrical demand in [W]
        "P_Wind": 0.0,                          # electrical power output from local wind generation in [W]
        "m_gasdemand": 0.0                      # chemical local gasdemand in [kg/s]
    },
    "metadata": {
        "direction_pow_demand": os_path.join(dirname, '../EMS/library/Daten/el_load_Hafen_KA_2017.mat'),
        "direction_heat_demand": os_path.join(dirname, '../EMS/library/Daten/heat_demand_Hafen_KA_2017.mat'),
        "weather_data": os_path.join(dirname, '../EMS/library/Daten/tmy_EnergiebergKA_2007_2016.mos'),
        #"weather_data": os_path.join(dirname, '../EMS/library/Daten/KIT_CN_weather.mos'),
        "fmu_directory": os_path.join(dirname, '../Modelle/MGRID_0ch_FMU_UseCase_UseCase_02020_010_030_NEU.fmu'),
        "name": "Usecase",
        "EMS": {
            "name": "Usecase",
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/LUT/Usecase_data'),
            "steering": False,
            "Outputs": ["time", "P_Wind", "P_PV", "m_gasdemand", "P_el_demand"],
            "type": "Prediction"
        }
    }
}
facility_dict[usecase_parameters["metadata"]["name"]] = usecase_parameters


electricitygrid_parameters = {
    "input": {

    },
    "output": {
        "Electricity_demand_W": 0.0,               # W
        "Electricity_demand_price": 0.0,            # €/MWh
    },
    "metadata": {
        "table_directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Electricity_grid_2019'),
        "name": "Electricitygrid",
        "EMS": {
            "name": "Electricitygrid",
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Electricity_grid_2019'),
            "steering": False,
            "Outputs": ["time", "price", "P_el"],
            "type": "Prediction"
        }
    }
}
facility_dict[electricitygrid_parameters["metadata"]["name"]] = electricitygrid_parameters



gasgrid_parameters = {
    "input": {

    },
    "output": {
        "gas_demand_m3_h": 0.0,                 # m^3/h
        "gas_demand_m3_s": 0.0,                 # m^3/s
        "gas_demand_kw": 0.0,                   # kW
        "gas_demand_Brennwert": 0.0,            # kWh/m^3
        "gas_demand_price_kwh": 0.0,            #€/kWh
        "gas_demand_price_Mwh": 0.0,            #€/MWh
        "gas_demand_price_J": 0.0,              #€/J (€/Ws)
        "gas_demand_kg_s": 0.0                  #kg/s
    },
    "metadata": {
        "table_directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Gasdemand_test'),
        "name": "Gasgrid",
        "EMS": {
            "name": "Gasgrid",
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Gasdemand_test'),
            "steering": False,
            "Outputs": ["time", "value", "Brennwert", "gas_demand_price_kwh"],
            "type": "Prediction"
        }
    }
}
facility_dict[gasgrid_parameters["metadata"]["name"]] = gasgrid_parameters

gasstorage_parameters = {
    "input": {
        "Eta": 0.995,
        "m_Gasstorage_max": 1000/(60*60),
        "mass_Gasstorage_0": 250*6,
        "mass_Gasstorage_max": 500*6,
        "X_CH4_set": 0
    },
    "output": {
        "mass_Gasstorage": 0.0,
        "SOC_Gasstorage": 0.0,
        "m_Gasstorage": 0.0,                 # m^3/s
    },
    "metadata": {
        "table_directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Gasdemand_test'),          #table_directory oder einfach directory
        "name": "Gasstorage",
        "EMS": {
            "eta": 0.995,                                       # can
            "E_max": 500 * 6,                                   # can
            "E_0": 250*6,                                       # can
            "P_max": 1000 / (60 * 60),                          # can
            "name": "Gasstorage",                               # must
            "Opt_Range": [-1, 1],                               # can
            "steering": True,                                   # must
            "Outputs": ["E", "P"],                              # must
            "type": "Storage"                                   # must
        }
    }
}
facility_dict[gasstorage_parameters["metadata"]["name"]] = gasstorage_parameters


campusnord_parameters = {
    "input": {

    },
    "output": {
        "time": 0,
        "P_el": 0.0,               # W
        "time_relative": 0.0
    },
    "metadata": {
        "table_directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/campus_nord'),
        "name": "campus_nord",
        "EMS": {
            "name": "campus_nord",
            #"Vorhersage":
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/campus_nord'),
            "steering": False,
            "type": "Prediction",
            "Outputs": ["time", "time_relative", "P_el"]
        }
    }
}
facility_dict[campusnord_parameters["metadata"]["name"]] = campusnord_parameters

lastreihe_parameters = {
    "input": {

    },
    "output": {

    },
    "metadata": {
        "name": "Lastreihe",
        "EMS": {
            "name": "Lastreihe",
            "directory": os_path.join(os_path.dirname(__file__), '../EMS/library/Daten/Lastreihe_CN_2019_corrected'),
            "steering": False,
            "Outputs": ["time", "P_el"],
            "type": "Prediction"
        }
    }
}
facility_dict[lastreihe_parameters["metadata"]["name"]] = lastreihe_parameters

token = ''
if __name__ == '__main__':
    tmp_dict = [{}]
    tmp_dict[0]["time"] = 0
    tmp_dict[0]["fields"] = {"parameters": json.dumps(facility_dict)}
    tmp_dict[0]["tags"] = {"SimID": "Simulationen_Diss"}
    tmp_dict = dumps(tmp_dict)
    url = config.DB + config.metric
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    response = request("POST", url, headers=headers, data=tmp_dict)
    print(response.text)
