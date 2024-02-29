##########
# Import #
##########
# Data retrieval and wrangling
import pandas as pd
import modules.data_retrieval.retrieve_sets_params as get_sets_params
import sqlite3
from contextlib import closing

# Travel time matrix
from sklearn.metrics.pairwise import haversine_distances
from math import radians
import modules.utils.utils as utils


#############
# Functions #
#############

def get_auditor_depot_matrix(con: sqlite3.Connection) -> dict[int, dict[int, int]]:
    """
    Returns the auditor-depot matrix.
    """
    with closing(con.cursor()) as cur:
        employee_depots = cur.execute("""SELECT
                                            facilities.ID AS facility_id,
                                            employees.ID AS employee_id
                                        FROM facilities
                                        INNER JOIN employees ON facilities.ID = employees.depot_id""").fetchall()
        depots = get_sets_params.get_depots(con)
        return_dict = {}
        for depot in depots:
            return_dict[depot] = {}
        
        for dep, empl in employee_depots:
            for depot in depots:
                if depot == dep:
                    return_dict[depot][empl] = 1
                else:
                    return_dict[depot][empl] = 0
    return return_dict


def get_travel_time_matrix(audits: pd.DataFrame,
                        depots: list[int],
                        con: sqlite3.Connection,
                        km_pr_hour: int = 80) -> dict[dict[float]]:
    """
    Returns the travel-time matrix.
    """
    physical_audits = audits[audits["on_site_audit"] == 1]
    locations = []
    for depot in depots:
        for _, coords in utils.get_lat_long(con, depot).items():
            locations.append([radians(coord) for coord in coords])
                

    for i, row in physical_audits.iterrows():
        locations.append([radians(row["long"]), radians(row["lat"])])

    distance_matrix = {
    }

    distances = (haversine_distances(locations) * (6371000/1000)) / km_pr_hour
    for i, id_1 in enumerate([*depots, *physical_audits["ID"]]):
        distance_matrix[id_1]= {}
        for j, id_2 in enumerate([*depots, *physical_audits["ID"]]):
            distance_matrix[id_1][id_2] = distances[i][j]
    
    return distance_matrix


def get_accomplice_matrix(audits: pd.DataFrame,
                          con: sqlite3.Connection) -> dict[int, dict[int, int]]:
    """
    Returns the accomplice matrix
    """
    employees_tbl = pd.read_sql("SELECT * FROM employees", con)
    skills_tbl = pd.read_sql("SELECT * FROM skills", con)

    employees = employees_tbl["ID"].to_list()
    accomplice_matrix = {}

    for empl in employees:
        accomplice_matrix[empl] = {}

    for i, row in audits.iterrows():
        audit_id = row["ID"]
        audit_type = row["audit_type_id"]
        skill_req = row["required_skill_level"]
        for empl in employees:
            accomplice_matrix[empl][audit_id] = []
            skill_level = skills_tbl[(skills_tbl["employee_id"].astype(int) == int(empl)) & (skills_tbl["audit_type_id"].astype(int) == int(audit_type))]["skill_level"].to_list()[0]
            if skill_level >= skill_req:
                accomplice_matrix[empl][audit_id] = 1
            else:
                accomplice_matrix[empl][audit_id] = 0
    return accomplice_matrix