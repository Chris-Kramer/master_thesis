###########
# Imports #
###########
import sqlite3
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go

from modules.utils.date_utils import convert_date_to_id
from modules.simulation_model import run_sim_model

#######################
# Database Connection #
#######################
con = sqlite3.connect("final_database_master_thesis.db")
con.execute("PRAGMA foreign_keys = 1")
con.commit()

####################
# Simulation model #
####################
# ------ Initialization Routine -----
# Start parameters
vehicle_start_hour = 6
vehicle_end_hour = 18
km_pr_hour = 80
phi = 15
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-01-05", con)

run_sim_model(first_day,
              last_day,
              phi = phi,
              epsilon = 5,
              output_txt= "results/test_SECs/mtz_test.txt",
              output_csv = "results/test_SECs/mtz_test.csv",
              output_dict= "results/test_SECs/mtz_test.pkl",
              bornholm = False,
              green_land = False,
              holidays = False,
              sec = "mtz")

run_sim_model(first_day,
              last_day,
              phi = phi,
              epsilon = 5,
              output_txt= "results/test_SECs/adfj_test.txt",
              output_csv = "results/test_SECs/adfj_test.csv",
              output_dict= "results/test_SECs/adfj_test.pkl",
              bornholm=False,
              green_land=False,
              holidays=False,
              sec = "adfj")


run_sim_model(first_day,
              last_day,
              phi = phi,
              epsilon = 5,
              output_txt= "results/test_SECs/dfj_test.txt",
              output_csv = "results/test_SECs/dfj_test.csv",
              output_dict= "results/test_SECs/dfj_test.pkl",
              bornholm=False,
              green_land=False,
              holidays=False,
              sec = "dfj")
