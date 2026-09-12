import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

QUERY = """
SELECT
    f.flight_id,
    f.fl_date,
    f.carrier,
    f.origin,
    f.dest,
    f.crs_dep_time,
    f.crs_arr_time,
    f.dep_delay,
    f.arr_delay,
    r.leg_number,
    r.prev_crs_arr_time

FROM flights f
LEFT JOIN flight_rotations r ON r.flight_id = f.flight_id
WHERE f.arr_delay IS NOT NULL AND f.dep_delay IS NOT NULL
"""

def build():
    print("loading flights from postgres...")
    df = pd.read_sql(QUERY, engine)
    df["fl_date"] = pd.to_datetime(df["fl_date"])
    print(f"{len(df)} flights loaded from postgres")

    # schedule attributes, all present on the ticket
    df["dep_hour"] = df["crs_dep_time"] //100
    df["day_of_week"] = df["fl_date"].dt.dayofweek
    df["month"] = df["fl_date"].dt.month
    df["route"] = df["origin"] + "-" + df["dest"]

    # rotation attributes. derived from published schudules
    df["leg_number"] = df["leg_number"].fillna(1)

    prev_arr_mins = (df["prev_crs_arr_time"] // 100) * 60 + df["prev_crs_arr_time"] % 100
    dep_mins = (df["crs_dep_time"] // 100) * 60 + df["crs_dep_time"] % 100
    turnaround = dep_mins - prev_arr_mins

    # negative values indicate the previous leg was scheduled to arrive after
    # midnight relative to this departure; treat these as missing.
    turnaround = turnaround.where(turnaround.between(0, 720))
    df["scheduled_turnaround"] = turnaround.fillna(turnaround.median())

    # Split before computing statistics, so no test-period information leaks
    cutoff = pd.Timestamp("2026-03-01")
    train_mask = df["fl_date"] < cutoff


    # Historical averages, computed on training rows only
    carrier_delay = df.loc[train_mask].groupby("carrier")["arr_delay"].mean()
    df["carrier_avg_delay"] = df["carrier"].map(carrier_delay)

    route_delay = df.loc[train_mask].groupby("route")["arr_delay"].mean()
    df["route_avg_delay"] = df["route"].map(route_delay)

    origin_delay = df.loc[train_mask].groupby("origin")["dep_delay"].mean()
    df["origin_avg_delay"] = df["origin"].map(origin_delay)

    volume = (
        df.loc[train_mask]
        .groupby(["origin", "dep_hour"])["flight_id"]
        .count()
        .rename("origin_hourly_volume")
    )
    df = df.merge(volume, on=["origin", "dep_hour"], how="left")



    # Rotation lookup, used at prediction time when the aircraft is unknown
    rotation_lookup = (
        df.loc[train_mask]
        .groupby(["carrier", "dep_hour"])[["leg_number", "scheduled_turnaround"]]
        .mean()
        .reset_index()
    )
    rotation_lookup.to_parquet("model/rotation_lookup.parquet", index=False)


    #Fill gaps left by categories absent from the training period
    for col in ["carrier_avg_delay", "route_avg_delay", "origin_avg_delay",
                "origin_hourly_volume"]:
        df[col] = df[col].fillna(df[col].median())



    columns = [
        "flight_id", "fl_date", "carrier", "origin", "dest", "route",
        "dep_hour", "day_of_week", "month",
        "leg_number", "scheduled_turnaround",
        "carrier_avg_delay", "route_avg_delay", "origin_avg_delay",
        "origin_hourly_volume",
        "dep_delay", "arr_delay",
    ]
    out = df[columns]
    out.to_parquet("data/flight_features.parquet", index=False)
    print(f"Saved {len(out):,} flights to data/flight_features.parquet")
    print(f"Mean arrival delay: {out['arr_delay'].mean():.2f} minutes")


if __name__ == "__main__":
    build()