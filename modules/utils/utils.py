###########
# Imports #
###########
import sqlite3
from contextlib import closing

###########################
# Utility functions #
###########################
def get_max_dict_value(my_dict: dict) -> float:
    """
    Returns the highest numerical value in a dictionary
    """
    return max([val for _, val in my_dict.items()])


def get_audit_facility(audit_id: int, con: sqlite3.Connection) -> int:
    """
    Returns the facility ID from an audit ID
    """
    with closing(con.cursor()) as cur:
        return cur.execute(f"SELECT facility_id FROM all_tasks WHERE ID == {audit_id}").fetchone()[0]


def get_lat_long(con: sqlite3.Connection, facility_id: int) -> dict[list[float]]:
    """
    Returns a dictionary which contains the latitude and longitude of a facility.
    The key is the facility ID
    The return value is a list of floats.
    The first list value is the longitude, the last list value is the latitude
    """
    with closing(con.cursor()) as cur:
        facility_locations = cur.execute(f"""
                                         SELECT
                                            facilities.ID AS facility_id,
                                            facilities.lat,
                                            facilities.long
                                         FROM facilities
                                         WHERE facility_id = {facility_id}""").fetchall()    
        return_dict = {}
        for facility_location in facility_locations:
            facility_id = facility_location[0]
            lat = facility_location[1]
            long = facility_location[2]
            return_dict[facility_id] = [long, lat]
    return return_dict





