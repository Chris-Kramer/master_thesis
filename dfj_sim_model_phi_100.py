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
phi = 100
epsilon = 5
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-12-31", con)

run_sim_model(first_day,
              last_day,
              phi = phi,
              epsilon = 12,
              output_txt= "results/phi_100_new_model/phi_100.txt",
              output_csv = "results/phi_100_new_model/phi_100.csv",
              output_dict= "results/phi_100_new_model/phi_100.pkl")

# ----- Results 2022 -----
print("Cleaning data for map with results")
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-12-31", con)

# Get Data
results_df = pd.read_csv("results/phi_100_new_model/phi_100.csv")
results_df = results_df[results_df["on_site_audit"] == 1]
results_2022 = results_df[(results_df["release_date_id"] >= first_day) &
                      (results_df["release_date_id"] <= last_day)]
results_2022 = results_2022[~((results_2022["zip_code"] >= 3700) & (results_2022["zip_code"] <= 3799))]
depots = pd.read_sql("SELECT * FROM facilities WHERE facilities.facility_type_id = 15", con)

# Get Depots
depots["Depot"] = ""
depots.loc[depots["ID"] == 1, "Depot"] = "DGA Odense"
depots.loc[depots["ID"] == 2, "Depot"] = "DGA Trekroner"
depots.loc[depots["ID"] == 3, "Depot"] = "DGA Fredensborg"
depots.loc[depots["ID"] == 4, "Depot"] = "DGA Aalborg"
depots.loc[depots["ID"] == 5, "Depot"] = "DGA Højbjerg"

# Remove NaN
results_2022 = results_2022.sort_values(by = "employee_id", ascending=True)
results_2022 = results_2022[results_2022["employee_id"].notna()]
results_2022["Auditor"] = results_2022["employee_id"].astype(str)

# Create map
print("Generating map of global results")
fig = px.scatter_mapbox(results_2022, 
                        lat="lat", 
                        lon="long",
                        opacity=0.7, 
                        color="Auditor",
                        hover_name= "facility_id", 
                        hover_data={"Auditor":True,  
                                    "lat":False, 
                                    "long":False,
                                    },
                        color_discrete_sequence=px.colors.qualitative.Light24,
                        zoom=8)


fig.add_trace(go.Scattermapbox(
    lat = depots["lat"],
    lon = depots["long"],
    mode='markers',
    marker=go.scattermapbox.Marker(
        size=15,
        color='rgb(0, 0, 0)',
        opacity=1
        ),
    name = "Depot"
    ))

fig.update_layout(mapbox_style="carto-positron")
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig.write_html("results/phi_100_new_model/phi_100.html")