##########
# Import #
##########

# Data retrieval and wrangling
import sqlite3
import pandas as pd
import numpy as np
import modules.data_retrieval.retrieve_sets_params as get_sets_params

# Relax release dates
from modules.relax_release_dates import relax_release_dates


##############################################
# Helper Functions for The output dictionary #
##############################################
def create_results_dict(con: sqlite3.Connection,
                        first_day: int,
                        last_day:int) -> dict:
    """
    Returns a dictionary, which stores the results of the simulation model
    """
    results_dict = {}
    for t in range(first_day, last_day + 1):
        results_dict[t] = {}
        for e in get_sets_params.get_employees(con):
            results_dict[t][e] = {}
            results_dict[t][e]["audits"] = []
    return results_dict  


def update_res_dict(results_dict: dict[int],
                     route_dict: dict,
                     audit_dict: dict,
                     day: int):
    """
    Updates the dictionary, which stores the results of the simulation model
    """
    for auditor, route in route_dict.items():
        results_dict[day][auditor]["route"] = route

    for auditor, audits in audit_dict.items():
        results_dict[day][auditor]["audits"] = audits                      
    
    return results_dict


###################
# Output CSV-file #
###################
def generate_simulation_dataframe(con: sqlite3.Connection,
                                  phi: int,
                                  epsilon: int,
                                  first_day: int,
                                  last_day:int) -> pd.DataFrame:
    """
    Is a wrapper for the function relax_release_dates.
    """
    all_audits = get_sets_params.get_all_audits(con)
    all_audits = all_audits[~((all_audits["zip_code"] >= 3700) & (all_audits["zip_code"] <= 3799))]
    all_audits = all_audits[all_audits["audit_type_id"] != 9]
    sim_audits = all_audits.copy()
    sim_audits["audit_date_id"] = np.nan
    sim_audits["employee_id"] = np.nan
    return relax_release_dates(phi, epsilon, sim_audits, first_day, last_day, con)
    