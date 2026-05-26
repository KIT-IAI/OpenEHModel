from schedule_generator import *
import facility_parameters
import numpy as np
import json
import os
import Daten.results.plotter as plotter
import requests
import pickle
import pandas as pd


# Read EA results and concats them into a single dataframe
# Time is reindexed to 15 minute intervals (900 seconds)
def read_ea_results(folder_path) -> pd.DataFrame:
    
    json_files = [f for f in os.listdir(folder_path) if f.endswith(".json")]
    targetDF = pd.DataFrame()
    for file in json_files:
        file_path = os.path.join(folder_path, file)
        json_results = json.load(open(file_path, "r"))
        times = list(range(0, 96))
        load = json_results["Lastreihe"]["P_el"]
        targetDF = pd.concat([targetDF, pd.DataFrame({"time": times, "Lastreihe": load})])
        # reindex time column
    targetDF = targetDF.reset_index(drop=True)
    targetDF["time"] = np.array(list(range(0, len(targetDF["time"])))) * 900
    return targetDF

