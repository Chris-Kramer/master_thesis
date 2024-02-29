import pandas as pd
import sqlite3
import modules.utils.utils as utils
import modules.utils.date_utils as date_utils
import modules.data_retrieval.retrieve_sets_params as get_sets_params


def relax_release_dates(phi: int,
                        epsilon: int,
                        all_audits: pd.DataFrame,
                        first_day: int,
                        last_day: int,
                        con: sqlite3.Connection) -> pd.DataFrame:
    for day in range(first_day, last_day + 1):
        all_audits = all_audits.sort_values(by = ["due_date_id", "duration", "priority_before_audit"], ascending= [True, False, False])
        all_audits = all_audits.reset_index(drop = True)
        day_audits = all_audits[(all_audits["release_date_id"] == day)].reset_index(drop = True).copy()

        all_audits = all_audits[(all_audits["release_date_id"] != day)].reset_index(drop = True)
        
        max_cap = utils.get_max_dict_value(get_sets_params.get_daily_employee_capacity(day, con))
        day_type = date_utils.get_day_type(day, con)
        if day_type != "workday":
            i = 1
            day_type = date_utils.get_day_type(day, con)
            while day_type != "workday":
                day_type = date_utils.get_day_type(day + i, con)
                i += 1            


            non_edit = day_audits[(day_audits["due_date_id"] + i <= (day - epsilon)) | (day_audits["release_date_id"] + i > last_day)].copy()
            edit_day = day_audits[~((day_audits["due_date_id"] + i <= (day - epsilon)) | (day_audits["release_date_id"] + i > last_day))].copy()
            edit_day = edit_day.reset_index(drop = True)
            non_edit = non_edit.reset_index(drop = True)

            edit_day["release_date_id"] = edit_day["release_date_id"] + i
            all_audits = pd.concat([all_audits, edit_day, non_edit])
        
        else:
            non_edit = day_audits[day_audits["due_date_id"] <= (day - epsilon)].copy()
            edit_day = day_audits[day_audits["due_date_id"] > (day - epsilon)].copy()
            edit_day = edit_day.reset_index(drop = True)
            non_edit = non_edit.reset_index(drop = True)

            if edit_day.shape[0] <= phi:
                all_audits = pd.concat([all_audits, non_edit, edit_day])

            else:
                edit_day.loc[phi : , "release_date_id"] = edit_day.loc[phi : , "release_date_id"].apply(lambda x : x+1)
                all_audits = pd.concat([all_audits, non_edit, edit_day])
    return all_audits
