###########
# Imports #
###########
# Data
import numpy as np
import pandas as pd
import sqlite3
from modules.data_retrieval.retrieve_sets_params import get_all_audits

# Output data
from modules.utils.output_utils import generate_simulation_dataframe
from modules.utils.output_utils import create_results_dict
from modules.utils.output_utils import update_res_dict
from modules.utils.output_utils import generate_auditor_dict
from modules.utils.output_utils import generate_day_dict
import pickle

# Sets and parameters
from modules.data_retrieval.retrieve_sets_params import get_audits_as_list
from modules.data_retrieval.retrieve_sets_params import get_on_site_audits
from modules.data_retrieval.retrieve_sets_params import get_depots
from modules.data_retrieval.retrieve_sets_params import get_employees
from modules.data_retrieval.retrieve_sets_params import get_due_dates
from modules.data_retrieval.retrieve_sets_params import get_objective_val 
from modules.data_retrieval.retrieve_sets_params import get_processing_times 
from modules.data_retrieval.retrieve_sets_params import get_n_vehicles 
from modules.data_retrieval.retrieve_sets_params import get_daily_employee_capacity 
from modules.data_retrieval.retrieve_sets_params import get_release_dates
from modules.data_retrieval.retrieve_sets_params import get_desk_audits

# Matrices
from modules.data_retrieval.retrieve_matrices import get_auditor_depot_matrix
from modules.data_retrieval.retrieve_matrices import get_accomplice_matrix
from modules.data_retrieval.retrieve_matrices import get_travel_time_matrix
from modules.data_retrieval.retrieve_matrices import get_distance_matrix

# Dates
from modules.utils.date_utils import convert_date_to_id
from modules.utils.date_utils import create_auditor_holidays
from modules.utils.date_utils import get_day_type

# Timing
import time
from math import sqrt
# Optimization
import gurobipy as gp
from gurobipy import GRB

import copy
from typing import Literal

#######################
# Database Connection #
#######################
con = sqlite3.connect("final_database_master_thesis.db")
con.execute("PRAGMA foreign_keys = 1")
con.commit()


##################
# DFJ SEC MODEL #
##################
def run_sim_model(first_day: int,
                  last_day: int,
                  phi: int,
                  epsilon: int,
                  output_txt = str,
                  output_csv = str,
                  output_dict = str,
                  vehicle_start_hour: int = 6,
                  vehicle_end_hour: int = 18,
                  km_pr_hour = 80,
                  holidays = True,
                  green_land = True,
                  bornholm = True,
                  sec: Literal["dfj", "adfj", "mtz"] = "dfj",
                  extend_horizon: bool = False) -> None:
    
    """
    Runs the simulation model with the DFJ SEC
    """
    # Txt for report generator
    f = open(output_txt, "w")
    total_travel_km = 0
    total_travel_time = 0
    total_audit_duration = 0
    total_throughput = 0
    flow_time = 0
    original_flow_time = 0
    total_auditor_capacity_dict = generate_auditor_dict(get_employees(con))
    total_auditor_travel_time_dict = generate_auditor_dict(get_employees(con))
    total_auditor_audit_time_dict = generate_auditor_dict(get_employees(con))
    total_auditor_fairness_dict = generate_auditor_dict(get_employees(con)) # f value
    total_daily_pref_score = generate_day_dict(first_day, last_day)

    if green_land:
        # Bornholm, Greenland, and holidays
        green_land_start, green_land_end = (first_day + 30, first_day + 37)
    if bornholm:
        bornholm_start, bornholn_end = (first_day + 30, first_day + 31)
    if holidays:
        auditor_holidays = create_auditor_holidays(first_day, last_day, con, 42)

    # Get and clean data
    all_audits = get_all_audits(con)
    all_audits = all_audits[~((all_audits["zip_code"] >= 3700) & (all_audits["zip_code"] <= 3799))] # Remove Bornholm
    all_audits = all_audits[all_audits["audit_type_id"] != 9] # Remove Greenland

    # Dataframe for simulation
    sim_audits = all_audits.copy()
    sim_audits["audit_date_id"] = np.nan
    sim_audits["employee_id"] = np.nan
    original_r = get_release_dates(sim_audits) # The original release dates
    sim_audits = generate_simulation_dataframe(con, phi, epsilon, first_day, last_day, extend_horizon)

    # Multi-day audits
    long_audits = sim_audits[sim_audits["duration"] > 8]["ID"].to_list()
    long_audits_last_audit = {}
    long_audits_auditors = {}
    for long_audit in long_audits:
        long_audits_auditors[long_audit] = None
        long_audits_last_audit[long_audit] = 0

    # Dictionary for output
    results_dict = create_results_dict(con, first_day, last_day)

    # ----- Timing routine -----
    start_time = time.time()
    for day in range(first_day, last_day + 1):


        # Get audits
        daily_audits = sim_audits[(sim_audits["release_date_id"] <= day) &
                                (sim_audits["release_date_id"] >= first_day) &
                                (sim_audits["audit_date_id"] < 0)]
        
        # Is it a workday and is there any audits?
        if daily_audits.shape[0] == 0:
            print(f"\n ############################ Day {day} ################################### \n")
            print(f"""\n No Audits Available \n""")
            
            f.write(f"\n ############################ Day {day} ################################### \n")
            f.write(f"""\n No Audits Available \n""")
            continue
    
        f.write(f"\n ############################ Day {day} ################################### \n")
        f.write(f"""\n N AUDITS: {daily_audits.shape[0]} \n""")
        print(f"\n ############################ Day {day} ################################### \n")
        print(f"""\n N AUDITS: {daily_audits.shape[0]} \n""")
        # ----- Event Routine -----
        # Get Data
        t = day
        O = get_on_site_audits(daily_audits)
        V = get_audits_as_list(daily_audits)
        L = get_depots(con)
        E = get_employees(con)
        d = get_due_dates(daily_audits)
        u = get_objective_val(d, t)
        b = get_auditor_depot_matrix(con)
        g = get_accomplice_matrix(daily_audits, con)
        p = get_processing_times(daily_audits)
        K = get_n_vehicles(t, con, vehicle_start_hour, vehicle_end_hour)
        q = get_daily_employee_capacity(t, con)
        c = get_travel_time_matrix(daily_audits, L, con, km_pr_hour)
        r = get_release_dates(daily_audits)
        c_kilometers = get_distance_matrix(daily_audits, L, con)
        desk_audits = get_desk_audits(daily_audits)


        # Split multi-day Audits
        for i in V:
            if i in long_audits:
                if p[i] - 5 > 0:
                    p[i] = 5
                else:
                    long_audits_last_audit[i] = 1
                
                # Update Accomplice matrix so it is the auditor who performs the multi-day audit
                if long_audits_auditors[i] is not None:
                    assigned_auditor = long_audits_auditors[i]
                    for e in E:
                        if e == assigned_auditor:
                            g[e][i] = 1
                        else:
                            g[e][i] = 0
        
        if green_land:
            # Set Employee 10 and 11 as unavailable for Greenland expedition
            if green_land_start <= day <= green_land_end:
                q[10] = 0
                q[11] = 0
        
        if bornholm:
            if bornholm_start <= day <= bornholn_end:
                q[2] = 0
                q[3] = 0

        if holidays:
            # Create Holidays #
            for e in E:
                start_holiday, end_holiday = auditor_holidays[e]
                if start_holiday <= day <= end_holiday:
                    q[e] = 0


        # Create Model
        m = gp.Model(f"Danzig-fuller-day-{day}")
        a = m.addVars(E, vtype=GRB.BINARY, name="a")
        y = m.addVars(V, E, vtype=GRB.BINARY, name="y")
        x = m.addVars([*O, *L],[*O, *L], E, vtype=GRB.BINARY, name="x") 
        
        if sec.lower() == "mtz":
            s = m.addVars(O, vtype=GRB.CONTINUOUS, name="s")
            Q = max([q[e] for e in E])       
        
        # Not necessary but improves performance
        for e in E:
            for l in L:
                for i in [*O, *L]:
                    if b[l][e] == 0:
                        x[l, i, e].ub = 0
                        x[i, l, e].ub = 0

        # Add constraints
        print("Constraint 1: Only leave once from designated depot")
        for e in E:
            for l in L:
                m.addConstr(gp.quicksum(x[l, i, e] for i in O) == b[l][e] * a[e])
        
        print("Constraint 2: Only return once from designated depot")
        for e in E:
            for l in L:
                m.addConstr(gp.quicksum(x[i, l, e] for i in O) == b[l][e] * a[e])
        
        print("Constraint 3: Respect vehicle capacity when leaving")
        for l in L:
            m.addConstr(gp.quicksum(x[i, l, e] for e in E for i in O) <= K[l])
        
        print("Constraint 4: Respect vehicle capacity when returning")
        for l in L:
            m.addConstr(gp.quicksum(x[l, i, e] for e in E for i in O) <= K[l])

        print("Constraint 5: Respect skill levels")
        for i in V:
            for e in E:
                m.addConstr(g[e][i] >= y[i, e])

        print("Constraint 6: No more than 1 audit")
        for i in V:
            m.addConstr(gp.quicksum(y[i, e] for e in E) <= 1)

        print("Constraint 6: Create Tour From --> To")
        for i in O:
            for e in E:
                m.addConstr(gp.quicksum(x[i, j, e] for j in [*O, *L]) == y[i, e])

        print("Constraint 7: Create Tour To --> From")        
        for i in O:
            for e in E:
                m.addConstr(gp.quicksum(x[j, i, e] for j in [*O, *L]) == y[i, e])

        print("Constraint 8: Do not go above employee capacity")
        for e in E:
            m.addConstr(gp.quicksum(c[i][j] * x[i, j, e] for i in [*O, *L] for j in [*O, *L]) + gp.quicksum(p[i] * y[i, e] for i in V) <= q[e])
        
        print("Constraint 9: Create assignment variable")
        for e in E:
            for i in O:
                m.addConstr(y[i, e] <= a[e])

        print("Constraint 10: Force y to 1")
        for i in V:
            m.addConstr(d[i] + gp.quicksum(y[i, e] for e in E) >= t + 2)
        
        print("Constraint 11: Conserve flow")
        for j in [*O, *L]:
            for e in E:
                m.addConstr(gp.quicksum(x[i, j, e] for i in [*O, *L]) - gp.quicksum(x[j, i, e] for i in [*O, *L]) == 0)

        if sec.lower() == "mtz":
            print("MTZ SEC")
            for e in E:
                for i in O:
                    for j in O:
                        m.addConstr(s[j] - s[i] >= p[j] - Q*(1 - x[i, j, e]))
            for i in O:
                m.addConstr(s[i] >= gp.quicksum(p[i] * y[i, e] for e in E))

            for i in O:
                m.addConstr(s[i] <= Q)
        
        if sec.lower()  == "dfj" or sec.lower()  == "adfj":
            # Subtour elimination
            def subtour_elimination_callback(model, where):
                if where == GRB.Callback.MIPSOL:
                    # Get the solution values
                    vals = model.cbGetSolution(model._vars)
                    selected_edges = [(i, j, e) for i in [*L, *O] for j in [*L, *O] for e in E if vals[i, j, e] > 0.6]
                    # Find subtours in the selected edges
                    S = get_subtours(selected_edges)
                    
                    # Add subtour elimination constraints
                    if len(S) != 1:
                        if sec.lower()  == "dfj":
                            for e in E:
                                for i in range(len(S)):
                                    model.cbLazy(gp.quicksum(model._vars[S[i][j][0], S[i][j][1], e] for j in range(len(S[i]))) <= len(S[i])-1)
                        elif sec.lower()  == "adfj":
                            for i in range(len(S)):
                                model.cbLazy(gp.quicksum(model._vars[S[i][j][0], S[i][j][1], e] for j in range(len(S[i])) for e in E) <= len(S[i])-1)    


            def get_subtours(r0):
                """
                This code is adapted from the sub-tour elimination procedure at this website:
                https://medium.com/swlh/techniques-for-subtour-elimination-in-traveling-salesman-problem-theory-and-implementation-in-71942e0baf0c   
                """
                r=copy.copy(r0)
                route = []
                while len(r) != 0:
                    plan = [r[0]]
                    del (r[0])
                    l = 0
                    while len(plan) > l:
                        l = len(plan)
                        for i, j in enumerate(r):
                            if plan[-1][1] == j[0]:
                                plan.append(j)
                                del (r[i])
                    route.append(plan)
                return(route)

        # Solve Model
        m._vars = x 
        m.Params.lazyConstraints = 1
        m.Params.TimeLimit = 6*(60*60)
        m.Params.NoRelHeurTime = 100
        try:
            # Objective function
            m.setObjective(gp.quicksum(y[i, e] * (1/u[i]) for i in V for e in E), GRB.MAXIMIZE)
            if sec.lower() != "mtz":
                m.optimize(subtour_elimination_callback)
            else:
                m.optimize()
        except Exception as e:
            print(f"Error: {e}")
            f.write(f"Error: {e} \n")

            print(" ###### Auditors ########")
            f.write(" ######## Auditors ######## \n")           
            for auditor in E:
                print(f"AUDITOR: {auditor} ######")
                print(f"\t - Availability: {q[auditor]}")      
                f.write(f"AUDITOR: {auditor} ###### \n")
                f.write(f"\t - Availability: {q[auditor]} \n")
            print()

            print(" ###### AUDITS ########")
            f.write(" ######## AUDITS ######## \n")
            for i in V:
                print(f"- Audit: {i}")
                f.write(f"- Audit: {i} \n")

                print(f"\t - Duration: {p[i]}")
                f.write(f"\t - Duration: {p[i]} \n")

                print(f"\t - Release Date: {r[i]}")
                f.write(f"\t - Release Date: {r[i]} \n")

                print(f"\t - Due Date: {d[i]}")
                f.write(f"\t - Due Date: {d[i]} \n")

                print(f"\t - Accomplice Matrix: {[g[e][i] for e in E]}")
                f.write(f"\t - Accomplice Matrix: {[g[e][i] for e in E]} \n")

                print(f"\t - Objective val: {u[i]}")
                f.write(f"\t - Objective val: {u[i]} \n")
            print()

            print(" ###### Depots ########")
            f.write("###### Depots ######## \n")
            for l in L:
                print(f"- Depot: {l}")
                f.write(f"- Depot: {l} \n")

                print(f"\t - Vehicle Capacity: {K[l]}")
                f.write(f"\t - Vehicle Capacity: {K[l]} \n")
            print()
            break

        if m.status == GRB.INFEASIBLE:
            f.write("\n MODEL IS INFEASIBLE !!! \n")
            
            
            print(" ###### Auditors ########")
            f.write(" ######## Auditors ######## \n")           
            for auditor in E:
                print(f"AUDITOR: {auditor} ######")
                print(f"\t - Availability: {q[auditor]}")      
                f.write(f"AUDITOR: {auditor} ###### \n")
                f.write(f"\t - Availability: {q[auditor]} \n")
            print()

            print(" ###### AUDITS ########")
            f.write(" ######## AUDITS ######## \n")
            for i in V:
                print(f"- Audit: {i}")
                f.write(f"- Audit: {i} \n")

                print(f"\t - Duration: {p[i]}")
                f.write(f"\t - Duration: {p[i]} \n")

                print(f"\t - Release Date: {r[i]}")
                f.write(f"\t - Release Date: {p[i]} \n")

                print(f"\t - Due Date: {d[i]}")
                f.write(f"\t - Due Date: {d[i]} \n")

                print(f"\t - Accomplice Matrix: {[g[e][i] for e in E]}")
                f.write(f"\t - Accomplice Matrix: {[g[e][i] for e in E]} \n")

                print(f"\t - Objective val: {u[i]}")
                f.write(f"\t - Objective val: {u[i]} \n")
            print()

            print(" ###### Depots ########")
            f.write("###### Depots ######## \n")
            for l in L:
                print(f"- Depot: {l}")
                f.write(f"- Depot: {l} \n")

                print(f"\t - Vehicle Capacity: {K[l]}")
                f.write(f"\t - Vehicle Capacity: {K[l]} \n")
            print()
            break
         
        # ----- Report Generator -----
        # Get Routes
        route_dict = {}
        for auditor in E:
            route_dict[auditor] = [(i, j) for i in [*O, *L] for j in [*O, *L] if x[i, j, auditor].X >= 0.6]

        # Get Audits
        audit_dict = {}
        for auditor in E:
            audit_dict[auditor] = [(i) for i in V if y[i, auditor].X >= 0.6]
        
        for auditor in E:
            total_audit_duration += sum([p[i] for i in O if y[i, auditor].X >= 0.6])

        # Print and Write Results
        print(f"""\n - Objective value: {m.objVal} \n\n""")
        n_auditors = 0
        daily_pref_score = 0
        for auditor, audits in audit_dict.items():
            audit_time = sum([p[audit] for audit in audits])
            travel_time = sum([c[i][j] for i, j in route_dict[auditor]])
            travel_km = sum([c_kilometers[i][j] for i, j in route_dict[auditor]])

            daily_desk_time = sum([p[audit] for audit in audits if audit in desk_audits])
            daily_on_site_time = sum([p[audit] for audit in audits if audit in O])

            if audit_time > 0:
                n_auditors += 1
                daily_pref_score += abs(((daily_on_site_time + travel_time) / (audit_time + travel_time)) - (daily_desk_time / (audit_time + travel_time)))

            total_auditor_capacity_dict[auditor] += q[auditor]
            total_auditor_audit_time_dict[auditor] += audit_time
            total_auditor_travel_time_dict[auditor] += travel_time

            total_travel_km += travel_km
            total_travel_time += travel_time
            total_throughput += len(audits)

            print(f"##### AUDITOR: {auditor} ######")
            print(f"Availability: {q[auditor]}")
            print(f"Total Audit Time: {audit_time}")
            print(f"Total Travel Time: {travel_time}")
            print(f"Total Time: {audit_time + travel_time}")
            print()
                    
            f.write(f"""\n - Objective value: {m.objVal} \n\n""")
            f.write(f"##### AUDITOR: {auditor} ###### \n\n")
            f.write(f"Availability: {q[auditor]} \n")
            f.write(f"Total Audit Time: {audit_time} \n")
            f.write(f"Total Travel Time: {travel_time} \n")
            f.write(f"Total Time: {audit_time + travel_time} \n \n")            


            print(" - AUDITS")
            f.write(" - AUDITS \n")
            for audit in audits:
                print(f"\t - Audit: {audit}")
                f.write(f"\t - Audit: {audit} \n")
            print()

            route = route_dict[auditor]
            print(f"\n - ROUTE\n")
            f.write(f"\n - ROUTE\n")
            if len(route) > 0:
                for i, j in route:
                    print(f"\t - FROM {i} --> {j}")
                    f.write(f"\t - FROM {i} --> {j} \n")
                f.write("\n")
                print()
        
        if n_auditors > 0:
            mean_daily_pref_score = daily_pref_score / n_auditors
            total_daily_pref_score[t] += mean_daily_pref_score

        # Update  Audits
        for auditor, audits in audit_dict.items():        
            for i in audits:
                if i in long_audits:
                    sim_audits.loc[sim_audits["ID"] == i, "duration"] = sim_audits.loc[sim_audits["ID"] == i, "duration"] - p[i]
                    
                    if long_audits_auditors[i] is None:
                        long_audits_auditors[i] = auditor

                    if long_audits_last_audit[i]  == 1:
                        sim_audits.loc[sim_audits["ID"] == i, "audit_date_id"] = day
                        sim_audits.loc[sim_audits["ID"] == i, "employee_id"] = auditor

                        flow_time += day - r[i]
                        original_flow_time += day - original_r[i]

                elif i not in long_audits:
                    sim_audits.loc[sim_audits["ID"] == i, "audit_date_id"] = day
                    sim_audits.loc[sim_audits["ID"] == i, "employee_id"] = auditor
                    flow_time += day - r[i]
                    original_flow_time += day - original_r[i]
        
        results_dict = update_res_dict(results_dict, route_dict, audit_dict, day)


    for e in E:
        total_auditor_fairness_dict[e] = (total_auditor_travel_time_dict[e] + total_auditor_audit_time_dict[e]) / total_auditor_capacity_dict[e]        
    mean_fairness = sum([total_auditor_fairness_dict[e] for e in E]) / len(E)
    total_fairness_mean_deviation = sum([abs(total_auditor_fairness_dict[e] - mean_fairness) for e in E]) / len(E)
    total_sched_score = sum([total_daily_pref_score[t] for t in total_daily_pref_score.keys()]) / (last_day - first_day)
    
    print()

    total_fuel_consumption = total_travel_km / 15
    total_co2 = total_fuel_consumption * 2.31
    C_max = max(sim_audits['audit_date_id'].to_list())
    C_max_0 = max(sim_audits[(sim_audits['audit_date_id'] & sim_audits["priority_before_audit"] == 0)]["audit_date_id"].to_list())
    C_max_1 = max(sim_audits[(sim_audits['audit_date_id'] & sim_audits["priority_before_audit"] == 1)]["audit_date_id"].to_list())
    C_max_2 = max(sim_audits[(sim_audits['audit_date_id'] & sim_audits["priority_before_audit"] == 2)]["audit_date_id"].to_list())
    C_max_3 = max(sim_audits[(sim_audits['audit_date_id'] & sim_audits["priority_before_audit"] == 3)]["audit_date_id"].to_list())
    weighted_make_span = (28 * C_max_3) + (14 * C_max_2) + (4 * C_max_1) + (C_max_0)
    print("--- %s seconds to run ---" % (time.time() - start_time))

    f.write(f"\n\n ############## Performance Measures ########## \n\n")
    f.write(f"- Fairness Absolute Mean Deviation: {round(total_fairness_mean_deviation, 4)} \n")
    f.write(f"- Schedule Score: {round(total_sched_score, 4)} \n")
    f.write(f"- Make-span: {C_max} \n")
    f.write(f"- Weighted Make-span: {weighted_make_span} \n")
    f.write(f"- Simulated Flow time: {flow_time} \n")
    f.write(f"- Simulated Mean Flow time: {round(flow_time / total_throughput, 2)} days \n")
    f.write(f"- Original Flow time: {original_flow_time} \n")
    f.write(f"- Original Mean Flow time: {round(original_flow_time / total_throughput, 2)} days \n")
    f.write(f"- Total Throughput: {round(total_throughput, 2)} audits \n")
    f.write(f"- Total Audit Duration: {round(total_audit_duration, 2)} hours \n")
    f.write(f"- Total Km Travelled: {round(total_travel_km, 2)} km. \n")
    f.write(f"- Normalized Km Travelled: {round(total_travel_km / total_audit_duration, 2)} km. pr. audit hour \n")
    f.write(f"- Total petrol consumption: {round(total_fuel_consumption, 2)} liters \n")
    f.write(f"- Normalized petrol consumption: {round(total_travel_km / total_fuel_consumption, 2)} liters pr. audit hour.\n")
    f.write(f"- Total CO2 Emissions: {round(total_co2, 2)} kg. \n")
    f.write(f"- Normalized CO2 Emissions: {round(total_travel_km / total_co2, 2)} kg. pr. audit hour. \n")
    f.write(f"- Total Travel Time: {round(total_travel_time, 2)} hours \n")
    f.write(f"- Normalized Travel Time: {round(total_travel_time / total_audit_duration,2)} hours pr. audit hour. \n \n")
    f.write("--- %s seconds to run ---" % (time.time() - start_time))

    # Save Final results
    sim_audits.to_csv(output_csv, index = False)
    with open(output_dict, 'wb') as fp:
        pickle.dump(results_dict, fp) 
    f.close()  

