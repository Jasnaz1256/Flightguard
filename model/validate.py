"""Validate the risk pipeline against historical connections."""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

sys.path.append(str(Path(__file__).resolve().parent.parent))

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

SAMPLE_QUERY = """
SELECT
    c.buffer_minutes,
    c.missed_connection,
    inb.carrier   AS inb_carrier,
    inb.origin    AS inb_origin,
    inb.dest      AS inb_dest,
    inb.fl_date   AS inb_date,
    inb.crs_dep_time AS inb_dep,
    inb.crs_arr_time AS inb_arr,
    inb.arr_delay AS inb_actual_arr_delay,
    outb.carrier  AS outb_carrier,
    outb.origin   AS outb_origin,
    outb.dest     AS outb_dest,
    outb.crs_dep_time AS outb_dep,
    outb.crs_arr_time AS outb_arr,
    outb.dep_delay AS outb_actual_dep_delay
FROM connections c
JOIN flights inb  ON inb.flight_id  = c.inbound_flight_id
JOIN flights outb ON outb.flight_id = c.outbound_flight_id
WHERE inb.fl_date >= '2026-03-01'
ORDER BY random()
LIMIT %(n)s;
"""


def measure_correlation(df):
    """Correlation between the inbound's arrival delay and the outbound's departure delay."""
    rho = df["inb_actual_arr_delay"].corr(df["outb_actual_dep_delay"])
    print(f"Measured delay correlation: {rho:.3f}")
    print(f"  (risk.py currently assumes 0.07)")
    return rho


def validate_predictions(df, n_show=10):
    """Compare predicted miss probabilities against observed outcomes."""
    from api.predictor import predict_connection
    from api.schemas import Flight

    predictions = []
    for _, row in df.iterrows():
        inbound = Flight(
            carrier=row["inb_carrier"], origin=row["inb_origin"], dest=row["inb_dest"],
            fl_date=row["inb_date"], crs_dep_time=int(row["inb_dep"]),
            crs_arr_time=int(row["inb_arr"]),
        )
        outbound = Flight(
            carrier=row["outb_carrier"], origin=row["outb_origin"], dest=row["outb_dest"],
            fl_date=row["inb_date"], crs_dep_time=int(row["outb_dep"]),
            crs_arr_time=int(row["outb_arr"]),
        )
        result = predict_connection(inbound, outbound)
        predictions.append(result["miss_probability"])

    df = df.copy()
    df["predicted"] = predictions

    print(f"\nOverall predicted miss rate: {df['predicted'].mean():.1%}")
    print(f"Overall actual miss rate:    {df['missed_connection'].mean():.1%}")

    # Group predictions into bands and compare with observed rates.
    bands = [0, 0.02, 0.05, 0.10, 0.20, 0.40, 1.0]
    df["band"] = pd.cut(df["predicted"], bands)
    summary = df.groupby("band", observed=True).agg(
        n=("missed_connection", "size"),
        predicted=("predicted", "mean"),
        actual=("missed_connection", "mean"),
    )
    print("\nCalibration by predicted-probability band:")
    print(summary.to_string(float_format=lambda x: f"{x:.3f}"))

    return df


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    print(f"Sampling {n} March connections ...")
    df = pd.read_sql(SAMPLE_QUERY, engine, params={"n": n})

    measure_correlation(df)
    validate_predictions(df)