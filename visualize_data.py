###########
# Imports #
###########
from modules.utils.output_utils import generate_simulation_dataframe
from modules.utils.date_utils import convert_date_to_id
from modules.utils.date_utils import convert_id_to_date
from modules.visualizations.generate_visualizations import generate_barchart_of_release_dates
from modules.data_retrieval.retrieve_sets_params import get_all_audits
import sqlite3
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go


#######################
# Database connection #
#######################
print("Connecting to Database")
con = sqlite3.connect("final_database_master_thesis.db")
cur = con.cursor()

###############################
# Barchart with release dates #
###############################
print("--------------- Bar Chart with release dates-------------------")
# ---- Initialization -----
epsilon = 5
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-12-31", con)


# ----- Barchart: Original release dates -----
print("Generating Barchart with release dates: original")
generate_barchart_of_release_dates(df = get_all_audits(con), 
                                   y_axis_range = 461,
                                   first_day = first_day,
                                   last_day = last_day,
                                   con = con).write_html("outputs/imgs/barchart_original_release_dates.html")

# ----- Barchart: phi = 100 -----
print("Generating Barchart with release dates: phi = 100")
sim_df = generate_simulation_dataframe(con = con,
                                       phi = 100,
                                       epsilon = epsilon,
                                       first_day = first_day,
                                       last_day = last_day)

fig = generate_barchart_of_release_dates(df = sim_df, 
                                   y_axis_range = 461,
                                   first_day = first_day,
                                   last_day = last_day,
                                   con = con)
fig.add_hline(y=100)
fig.write_html("outputs/imgs/barchart_phi_100.html")

# ----- Barchart: phi = 50 -----
print("Generating Barchart with release dates: phi = 50")
sim_df = generate_simulation_dataframe(con = con,
                                       phi = 50,
                                       epsilon = epsilon,
                                       first_day = first_day,
                                       last_day = last_day)

fig = generate_barchart_of_release_dates(df = sim_df, 
                                   y_axis_range = 461,
                                   first_day = first_day,
                                   last_day = last_day,
                                   con = con)
fig.add_hline(y=50)
fig.write_html("outputs/imgs/barchart_phi_50.html")

# ----- Barchart: phi = 15 -----
print("Generating Barchart with release dates: phi = 15")
sim_df = generate_simulation_dataframe(con = con,
                                       phi = 15,
                                       epsilon = epsilon,
                                       first_day = first_day,
                                       last_day = last_day)

fig = generate_barchart_of_release_dates(df = sim_df, 
                                   y_axis_range = 461,
                                   first_day = first_day,
                                   last_day = last_day,
                                   con = con)
fig.add_hline(y=15)
fig.write_html("outputs/imgs/barchart_phi_15.html")

# ----- Barchart: phi = 6 -----
print("Generating Barchart with release dates: phi = 6")
sim_df = generate_simulation_dataframe(con = con,
                                       phi = 6,
                                       epsilon = epsilon,
                                       first_day = first_day,
                                       last_day = last_day)

fig = generate_barchart_of_release_dates(df = sim_df, 
                                   y_axis_range = 461,
                                   first_day = first_day,
                                   last_day = last_day,
                                   con = con)
fig.add_hline(y=6)
fig.write_html("outputs/imgs/barchart_phi_6.html")

########
# Maps #
########

print("--------------- Routing maps -------------------")

# ----- Get Data -----
print("Getting data for maps")
facilities_tbl = pd.read_sql("""SELECT
                                facilities.ID,
                                facilities.name,
                                facilities.n_machines,
                                facilities.n_betting,
                                facilities.facility_type_id,
                                facilities.active,
                                facilities.active,
                                facilities.address,
                                facilities.zip_code,
                                facilities.city,
                                facilities.country,
                                facilities.lat,
                                facilities.long,
                                districts.employee_id,
                                employees.name AS employee_name,
                                employees.depot_id
                             FROM facilities
                             INNER JOIN districts
                                ON (facilities.zip_code = districts.zip_code
                                AND facilities.facility_type_id = districts.facility_type_id)
                             INNER JOIN employees
                                ON employees.ID = districts.employee_id""", con)


depots = pd.read_sql("SELECT * FROM facilities WHERE facilities.facility_type_id = 15", con)

depots["Depot"] = ""

depots.loc[depots["ID"] == 1, "Depot"] = "DGA Odense"
depots.loc[depots["ID"] == 2, "Depot"] = "DGA Trekroner"
depots.loc[depots["ID"] == 3, "Depot"] = "DGA Fredensborg"
depots.loc[depots["ID"] == 4, "Depot"] = "DGA Aalborg"
depots.loc[depots["ID"] == 5, "Depot"] = "DGA Højbjerg"

facilities_tbl["Depot"] = ""

facilities_tbl.loc[facilities_tbl["depot_id"] == 1, "Depot"] = "DGA Odense"
facilities_tbl.loc[facilities_tbl["depot_id"] == 2, "Depot"] = "DGA Trekroner"
facilities_tbl.loc[facilities_tbl["depot_id"] == 3, "Depot"] = "DGA Fredensborg"
facilities_tbl.loc[facilities_tbl["depot_id"] == 4, "Depot"] = "DGA Aalborg"
facilities_tbl.loc[facilities_tbl["depot_id"] == 5, "Depot"] = "DGA Højbjerg"


# ----- Global Routing -----
print("Generating map of global routing")
fig = px.scatter_mapbox(facilities_tbl, 
                        lat="lat", 
                        lon="long",
                        opacity=0.7, 
                        hover_name= "ID", 
                        hover_data={"ID":True,  
                                    "lat":False, 
                                    "long":False,
                                    },
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
fig.write_html("outputs/imgs/global_routing.html")


# ----- Local Routing -----
print("Generating map of local routing")
local_dist_df = facilities_tbl.copy()
local_dist_df = local_dist_df.sort_values(by = "employee_id", ascending=True)
local_dist_df["Auditor"] = local_dist_df["employee_id"].astype(str)
fig = px.scatter_mapbox(local_dist_df, 
                        lat="lat", 
                        lon="long",
                        opacity=0.7, 
                        hover_name= "ID", 
                        hover_data={"Auditor":True,  
                                    "lat":False, 
                                    "long":False,
                                    },
                        color="Auditor",
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
fig.write_html("outputs/imgs/local_routing.html")


# ----- Semi-global Routing -----
print("Generating map of semi-global routing")
depot_viz = facilities_tbl[facilities_tbl["depot_id"].notna()]
fig = px.scatter_mapbox(depot_viz, 
                        lat="lat", 
                        lon="long",
                        opacity=0.7, 
                        hover_name= "ID", 
                        hover_data={"depot_id":True,  
                                    "lat":False, 
                                    "long":False,
                                    },
                        color="Depot",
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
fig.write_html("outputs/imgs/semi_global_routing.html")


# ----- Results 2022 -----
print("Cleaning data for map with results")
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-12-31", con)

# Get Data
results_df = pd.read_csv("outputs/results/model_holidays.csv")
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
fig.write_html("outputs/imgs/model_routing.html")

# ----- DGA districts 2022 -----
print("Getting and cleaning data of DGA districts 2022")
first_day = convert_date_to_id("2022-01-01", con)
last_day = convert_date_to_id("2022-12-31", con)

# Get Data
tasks = pd.read_sql("""SELECT
                                all_tasks.ID,
                                all_tasks.facility_id,
                                all_tasks.release_date_id,
                                all_tasks.audit_type_id,
                                facilities.zip_code,
                                facilities.facility_type_id,
                                facilities.lat,
                                facilities.long,
                                audit_types.on_site_audit,
                                districts.employee_id
                           FROM all_tasks
                           INNER JOIN audit_types ON all_tasks.audit_type_id = audit_types.ID
                           INNER JOIN facilities ON all_tasks.facility_id = facilities.ID
                           INNER JOIN districts ON facilities.facility_type_id = districts.facility_type_id AND facilities.zip_code = districts.zip_code
                           """, con)
tasks_2022 = tasks[(tasks["release_date_id"] >= first_day) &
                      (tasks["release_date_id"] <= last_day)]
tasks_2022 = tasks_2022[~((tasks_2022["zip_code"] >= 3700) & (tasks_2022["zip_code"] <= 3799))]
depots = pd.read_sql("SELECT * FROM facilities WHERE facilities.facility_type_id = 15", con)

depots["Depot"] = ""

depots.loc[depots["ID"] == 1, "Depot"] = "DGA Odense"
depots.loc[depots["ID"] == 2, "Depot"] = "DGA Trekroner"
depots.loc[depots["ID"] == 3, "Depot"] = "DGA Fredensborg"
depots.loc[depots["ID"] == 4, "Depot"] = "DGA Aalborg"
depots.loc[depots["ID"] == 5, "Depot"] = "DGA Højbjerg"


# Clean Data
tasks_2022 = tasks_2022.sort_values(by = "employee_id", ascending=True)
tasks_2022 = tasks_2022[tasks_2022["employee_id"].notna()]
tasks_2022["Auditor"] = tasks_2022["employee_id"].astype(str)


# Visulize map
print("Generating map of dga routing")
fig = px.scatter_mapbox(tasks_2022, 
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
fig.write_html("outputs/imgs/dga_routing.html")

###############
# Gantt Chart #
###############
print("--------------- Gantt Chart -------------------")
print("Getting and cleaning data")
# Get Data and convert it to datetime
all_audits = get_all_audits(con)
all_audits = all_audits.sort_values( "release_date_id").reset_index(drop = True)
all_audits = all_audits[(all_audits["release_date_id"] >= convert_date_to_id("2020-01-01", con)) & (all_audits["release_date_id"] <= convert_date_to_id("2024-12-31", con))]
all_audits["release_date"] =  all_audits["release_date_id"].apply(convert_id_to_date, con = con)
all_audits["release_date"] = pd.to_datetime(all_audits["release_date"])
all_audits["due_date"] =  all_audits["due_date_id"].apply(convert_id_to_date, con = con)
all_audits["due_date"] = pd.to_datetime(all_audits["due_date"])

# Visualize Gant chart
print("Generating Gant Chart")
all_audits["Audit"] = all_audits.index
fig = px.timeline(all_audits,
                  x_start="release_date",
                  opacity=1,
                  x_end="due_date",
                  y= "Audit")
fig.update_yaxes(autorange="reversed") # otherwise tasks are listed from the bottom up
fig.update_layout(
    plot_bgcolor='white'
)
fig.write_html("outputs/imgs/gantt_chart.html")


################################################
# Barchart with total audit duration each year #
################################################
print("--------------- Duration barchart -------------------")
print("Getting and cleaning data")
# Get Data and convert it to datetime
all_audits = get_all_audits(con)
all_audits = all_audits.sort_values( "release_date_id").reset_index(drop = True)
all_audits = all_audits[(all_audits["release_date_id"] >= convert_date_to_id("2020-01-01", con)) & (all_audits["release_date_id"] <= convert_date_to_id("2025-12-31", con))]
all_audits["release_date"] =  all_audits["release_date_id"].apply(convert_id_to_date, con = con)
all_audits["release_date"] = pd.to_datetime(all_audits["release_date"])
all_audits["due_date"] =  all_audits["due_date_id"].apply(convert_id_to_date, con = con)
all_audits["due_date"] = pd.to_datetime(all_audits["due_date"])

# Get total audit time for each year
all_audits = all_audits.groupby(all_audits.release_date.dt.year)["duration"].agg(['sum']).reset_index()
all_audits = all_audits.rename(columns={

    "release_date": "year"
})

# Visualize barchart
print("Generating chart")
all_audits = all_audits[all_audits["year"] >= 2020]
all_audits = all_audits[all_audits["year"] <= 2025]
fig = px.bar(all_audits, y = "sum", x="year", text_auto=True)
fig.update_layout(yaxis_range=[0, 25000])
fig.add_hline(y=19800) # 19800 is the maximum capacity
fig.write_html("outputs/imgs/yearly_audit_duration_barchart.html")


################################
# Histogram of audit durations #
################################
print("--------------- Histogram -------------------")
print("Getting and cleaning data")
all_audits = get_all_audits(con)
all_audits = all_audits.groupby(all_audits["duration"])['duration'].agg(['count']).reset_index()

print("Generating Histogram")
fig = px.histogram(all_audits, y = "count", x="duration", nbins=25, text_auto=True)
fig.write_html("outputs/imgs/durations_histogram.html")
