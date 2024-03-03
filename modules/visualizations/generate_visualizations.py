import pandas as pd
import sqlite3
import plotly.express as px

def generate_barchart_of_release_dates(df: pd.DataFrame,
                                       y_axis_range: int,
                                       first_day: int,
                                       last_day: int,
                                       con:sqlite3.Connection) -> px.bar:
    """
    Takes a dataframe containing all audits and generates a barchart showing the distribution of release dates.
    The barchart only displays dates between first_day and last day.
    The return value is a plotly figure. 
    """
    
    df["release_date_id"] = df["release_date_id"].astype(int)
    dates_tbl = pd.read_sql("SELECT * FROM dates", con)
    dates_tbl["ID"] = dates_tbl["ID"].astype(int)

    df = df[(df["release_date_id"] >= first_day) & (df["release_date_id"] <= last_day)]
    df = df.merge(dates_tbl, how="left", left_on="release_date_id", right_on="ID")
    df = df.groupby("date").size().reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns={0: "phi"})
    
    fig = px.bar(df, x = "date", y = "phi")
    fig = fig.update_layout(yaxis_range=[0, y_axis_range])
    return fig