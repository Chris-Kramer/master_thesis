
###########
# Imports #
###########
# Data retrieval and wrangling
import pandas as pd
import sqlite3
from contextlib import closing

# Dates
import modules.utils.date_utils as date_utils

########################
# Auxilliary functions #
########################

# ----- Returns data frames ------

def get_all_audits(con: sqlite3.Connection) -> pd.DataFrame:
    """ 
    Returns a dataframe containing all audits and geographic information
    """
    return pd.read_sql("""SELECT
                                all_tasks.ID,
                                all_tasks.facility_id,
                                all_tasks.release_date_id,
                                all_tasks.audit_date_id,
                                all_tasks.due_date_id,
                                all_tasks.duration,
                                all_tasks.audit_type_id,
                                all_tasks.required_skill_level,
                                all_tasks.priority_before_audit,
                                all_tasks.employee_id,
                                facilities.zip_code,
                                facilities.lat,
                                facilities.long,
                                audit_types.on_site_audit
                           FROM all_tasks
                           INNER JOIN audit_types ON all_tasks.audit_type_id = audit_types.ID
                           INNER JOIN facilities ON all_tasks.facility_id = facilities.ID
                           """, con)


def get_daily_audits(date: str,
                    con: sqlite3.Connection,
                    task_tbl: pd.DataFrame) -> pd.DataFrame:
    """
    Takes the dataframe from get_all_audits and returns the audits from a specific date ID
    """
    date_id = date_utils.convert_date_to_id(date, con)
    return task_tbl[task_tbl["release_date_id"].astype(int) == date_id]



# ----- Returns dictionaries -----

def get_daily_vehicle_capacity(date_id: int,
                               con: sqlite3.Connection,
                               start_hour: int = 7,
                               end_hour: int = 17) -> pd.DataFrame:
    time_slots = date_utils.get_date_time_slots(date_id, con)
    """
    Returns a dictionary that stores how many time slots a vehicle is available between a start hour and an end hour
    """
    time_slot_range = [time_slots[i] for i in range(start_hour, end_hour)]

    availability = pd.read_sql(f"SELECT * FROM vehicle_availability WHERE time_slot_id in {tuple(time_slot_range)}", con)
    availability = availability.groupby("vehicle_id", as_index=False)["available"].sum()
    vehicles = availability["vehicle_id"].to_list()
    capacity = availability["available"].to_list()

    return_dict = {
    }
    for vehicle, capacity in zip(vehicles, capacity):
        return_dict[vehicle] = capacity
    return return_dict


def get_depots_and_vehicles(con: sqlite3.Connection) -> dict[int, list[int]]:
    """
    Returns a dictionary containing a list of all vehicles associated with a depot.
    """
    with closing(con.cursor()) as cur:
        vehicle_depots = cur.execute("""SELECT
                                            facilities.ID AS facility_id,
                                            vehicles.ID AS vehicle_id
                                        FROM facilities
                                        INNER JOIN vehicles ON facilities.ID = vehicles.depot_id""").fetchall()
        return_dict = {}
        for depot, _ in vehicle_depots:
            return_dict[depot] = []
        
        for depot, vehicle in vehicle_depots:
            return_dict[depot].append(vehicle)
    return return_dict

################################
# Retrieve Sets and Parameters #
################################

# ----- Sets -----
def get_employees(con:sqlite3.Connection) -> list[int]:
    """
    Returns a list of auditors, which represent E
    """
    with closing(con.cursor()) as cur:
        employees = cur.execute("SELECT ID FROM employees").fetchall()
    return [em[0] for em in employees]


def get_vehicles(con:sqlite3.Connection) -> list[int]:
    """
    Returns a list of vehicles
    """
    with closing(con.cursor()) as cur:
        vehicles = cur.execute("SELECT ID FROM vehicles").fetchall()
    return [vehicle[0] for vehicle in vehicles]


def get_depots(con: sqlite3.Connection) -> list[int]:
    """
    Returns a list of depots, which represents L
    """
    with closing(con.cursor()) as cur:
        depots = cur.execute("""SELECT
                                    facilities.ID AS facility_id
                                FROM facilities
                                WHERE facilities.facility_type_id = 15""").fetchall()
    return [depot[0] for depot in depots]


def get_on_site_audits(audits: pd.DataFrame) -> list[int]:
    """
    Returns a list of on-site audits, which represent O
    """
    return [*audits[audits["on_site_audit"] == 1]["ID"]]


def get_audits_as_list(audits: pd.DataFrame) -> list[int]:
    """
    Returns a list of on-site audits, which represents V
    """
    return [*audits["ID"]]


# ----- Parameters ----- 

def get_processing_times(audits: pd.DataFrame) -> dict[int, int]:
    """
    Returns a dictionary of audit durations which represent p_i
    """
    durations = audits["duration"].to_list()
    audits = audits["ID"].to_list()
    p = {}
    for _, i in enumerate(audits):
        p[i] = durations[_]
    return p


def get_due_dates(audits: pd.DataFrame) -> dict[int, int]:
    """
    Returns a dictionary of due dates which represent d_i
    """
    tasks = audits["ID"].to_list()
    due_dates = audits["due_date_id"].astype(int).to_list()
    
    d = {}
    for task, due_date in zip(tasks, due_dates):
        d[task] = due_date
    return d


def get_daily_employee_capacity(date_id: str,
                                con: sqlite3.Connection) -> pd.DataFrame:
    """
    Returns a dictionary of daily auditor capacities, which represent q_e
    """
    time_slots = date_utils.get_date_time_slots(date_id, con)
    availability = pd.read_sql(f"SELECT * FROM employee_availability WHERE time_slot_id in {tuple(time_slots)}", con)
    
    availability = availability.groupby("employee_id", as_index=False)["available"].sum()
    employees = availability["employee_id"].to_list()
    capacity = availability["available"].to_list()

    q = {}
    for employee, capacity in zip(employees, capacity):
        q[employee] = capacity
    return q


def get_objective_val(due_dates: list[int], t: int) -> dict[int, int]:
    """
    Returns a dictionary which contains the difference between a list of due dates and the current date t.
    This represents u_i
    """
    u = {}
    for key, val in due_dates.items():
        u[key] = val - t
    return u


def get_n_vehicles(date_id: int,
                   con: sqlite3.Connection,
                   start_hour: int = 6,
                   end_hour: int = 18) -> dict[int, int]:
    """
    Returns a dictionary containing how many vehicles are available at each depot.
    This represents k_l
    """
    h = get_daily_vehicle_capacity(date_id,con, start_hour, end_hour)
    K = {}
    for depot, vehicles in get_depots_and_vehicles(con).items():
        K[depot] = 0
        for vehicle in vehicles:
            if h[vehicle] >= (end_hour - start_hour):
                K[depot] += 1
    return K

