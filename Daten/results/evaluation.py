import numpy as np
import json

from goal_functions import RMSE_function

def RMSE(ems_df):
    deviation =[]
    for i in range(len(ems_df)):
        if i == 96:
            last = -ems_df["Lastreihe"]["P_el"][96]
        else:
            last = -ems_df["Lastreihe"]["P_el"][i+1]
        deviation.append(last + ems_df["BHKW"]["P_el"][i] + ems_df["Battery"]["P"][i] + ems_df["Electrolyseur"]["P_el"][i])
    deviation = [power / 1000000 for power in deviation] # convert to MW
    deviation = [power / 4 for power in deviation] # 4 is the number of timesteps per hour
    deviation = [power ** 2 for power in deviation] # square the values
    deviation = sum(deviation) / len(deviation) # sum of the squared values divided by the number of values
    deviation = np.sqrt(deviation) # square root of the sum
    return deviation

def calculate_RMSE(milp_df, gleam_df):
    milp_RMSE = RMSE(milp_df)
    gleam_RMSE = RMSE(gleam_df)
    return milp_RMSE, gleam_RMSE

def load_df(path):
    with open(path, "r") as f:
        return json.load(f)

gleam_df = load_df("./26ground_truth_04_04_2022.0.json")
milp_df = load_df("./8gleam_ems_df20.json")

print("own", calculate_RMSE(milp_df, gleam_df))
print("ems", RMSE_function(milp_df, 0, 0), RMSE_function(gleam_df, 0, 0))