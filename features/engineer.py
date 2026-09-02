import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

QUERY = """
SELECT
    c.connection_id,
    c.buffer_minutes,
    c.missed_connection,
    c.airport,
    inb.carrier,
    inb.arr_delay        AS inbound_arr_delay,
    inb.dep_delay        AS inbound_dep_delay,
    inb.fl_date,
    outb.crs_dep_time    AS outbound_crs_dep
FROM connections c
JOIN flights inb  ON inb.flight_id  = c.inbound_flight_id
JOIN flights outb ON outb.flight_id = c.outbound_flight_id;
"""

def build():
    print("Loading connections from postgres ...")
    df = pd.read_sql(QUERY, engine)
    print(f"{len(df):,} rows loaded.")

    # derived features
    df["dep_hour"] = df["outbound_crs_dep"] // 100
    df["day_of_week"] = pd.to_datetime(df["fl_date"]).dt.dayofweek

    # Carrier reliability: share of that carrier's connections that were made
    carrier_miss_rate = df.groupby("carrier")["missed_connection"].transform("mean")
    df["carrier_ontime_rate"] = 1 - carrier_miss_rate

    # Congestion proxy: how many connections at this airport, this date, this hour
    df["airport_hourly_volume"] = df.groupby(
        ["airport", "fl_date", "dep_hour"]
    )["connection_id"].transform("count")

    features = df[[
        "connection_id", "fl_date",
        "inbound_arr_delay", "inbound_dep_delay", "buffer_minutes",
        "carrier_ontime_rate", "airport_hourly_volume",
        "dep_hour", "day_of_week",
        "missed_connection",
    ]]

    features.to_parquet("data/features.parquet", index=False)
    print(f"Saved {len(features):,} rows, miss rate {features['missed_connection'].mean():.4f}")


if __name__ == "__main__":
    build()