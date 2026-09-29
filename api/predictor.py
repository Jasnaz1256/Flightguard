"""Prediction logic for FlightGuard: features, models, and risk."""

import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from model.risk import connection_risk

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"

_bundle = joblib.load(MODEL_DIR / "flightguard_delay.pkl")
ARRIVAL_MODELS = _bundle["arrival_models"]
DEPARTURE_MODELS = _bundle["departure_models"]
FEATURES = _bundle["features"]
ENCODERS = _bundle["encoders"]
QUANTILES = _bundle["quantiles"]

CARRIER_LOOKUP = pd.read_parquet(MODEL_DIR / "carrier_lookup.parquet")
ROUTE_LOOKUP = pd.read_parquet(MODEL_DIR / "route_lookup.parquet")
ORIGIN_LOOKUP = pd.read_parquet(MODEL_DIR / "origin_lookup.parquet")
VOLUME_LOOKUP = pd.read_parquet(MODEL_DIR / "volume_lookup.parquet")
ROTATION_LOOKUP = pd.read_parquet(MODEL_DIR / "rotation_lookup.parquet")

DEFAULT_CARRIER_DELAY = float(CARRIER_LOOKUP["carrier_avg_delay"].median())
DEFAULT_ROUTE_DELAY = float(ROUTE_LOOKUP["route_avg_delay"].median())
DEFAULT_ORIGIN_DELAY = float(ORIGIN_LOOKUP["origin_avg_delay"].median())
DEFAULT_VOLUME = float(VOLUME_LOOKUP["origin_hourly_volume"].median())
DEFAULT_LEG = float(ROTATION_LOOKUP["leg_number"].median())
DEFAULT_TURNAROUND = float(ROTATION_LOOKUP["scheduled_turnaround"].median())


def _lookup(table, key, column, default):
    """Read a value from a single-key lookup table, falling back to a default."""
    try:
        return float(table.loc[key, column])
    except (KeyError, TypeError):
        return default


def _lookup_pair(table, key1, key2, column, default):
    """Read a value from a two-key lookup table, falling back to a default."""
    try:
        return float(table.loc[(key1, key2), column])
    except (KeyError, TypeError):
        return default

def build_features(flight) -> pd.DataFrame:
    """Reconstruct the model's feature vector from a booking's details."""
    route = f"{flight.origin}-{flight.dest}"
    dep_hour = flight.crs_dep_time // 100

    # Historical averages, read from the tables saved during training.
    carrier_delay = _lookup(CARRIER_LOOKUP, flight.carrier, "carrier_avg_delay", DEFAULT_CARRIER_DELAY)
    route_delay = _lookup(ROUTE_LOOKUP, route, "route_avg_delay", DEFAULT_ROUTE_DELAY)
    origin_delay = _lookup(ORIGIN_LOOKUP, flight.origin, "origin_avg_delay", DEFAULT_ORIGIN_DELAY)

    volume = _lookup_pair(VOLUME_LOOKUP, flight.origin, dep_hour, "origin_hourly_volume", DEFAULT_VOLUME)

    # Rotation attributes cannot be known for a future flight, so we use the
    # typical values for this carrier at this hour.
    rotation = ROTATION_LOOKUP[
        (ROTATION_LOOKUP["carrier"] == flight.carrier)
        & (ROTATION_LOOKUP["dep_hour"] == dep_hour)
    ]
    if len(rotation):
        leg_number = float(rotation["leg_number"].iloc[0])
        turnaround = float(rotation["scheduled_turnaround"].iloc[0])
    else:
        leg_number, turnaround = DEFAULT_LEG, DEFAULT_TURNAROUND

    row = {
        "dep_hour": dep_hour,
        "day_of_week": flight.fl_date.weekday(),
        "leg_number": leg_number,
        "scheduled_turnaround": turnaround,
        "carrier_avg_delay": carrier_delay,
        "route_avg_delay": route_delay,
        "origin_avg_delay": origin_delay,
        "origin_hourly_volume": volume,
        "carrier_enc": ENCODERS["carrier"].get(flight.carrier, -1),
        "origin_enc": ENCODERS["origin"].get(flight.origin, -1),
        "dest_enc": ENCODERS["dest"].get(flight.dest, -1),
        "route_enc": ENCODERS["route"].get(route, -1),
    }
    return pd.DataFrame([row])[FEATURES]


def _risk_band(probability):
    if probability < 0.05:
        return "low"
    if probability < 0.20:
        return "moderate"
    if probability < 0.50:
        return "high"
    return "very high"


def _forecast(quantiles):
    return {
        "p10": round(quantiles[0], 1),
        "p50": round(quantiles[2], 1),
        "p90": round(quantiles[4], 1),
    }


def _explain(result, buffer, arrival_quantiles):
    median_delay = arrival_quantiles[2]
    parts = [f"Your scheduled connection time is {buffer} minutes."]
    if median_delay > 0:
        parts.append(f"The inbound flight typically arrives about {median_delay:.0f} minutes late.")
    else:
        parts.append(f"The inbound flight typically arrives about {abs(median_delay):.0f} minutes early.")
    parts.append(
        f"Allowing for both flights' variability, you would usually have around "
        f"{result['median_time_available']:.0f} minutes at the gate."
    )
    return " ".join(parts)

def predict_connection(inbound, outbound, buffer_override=None):
    """Assess the risk of missing a connection between two flights."""
    inbound_features = build_features(inbound)
    outbound_features = build_features(outbound)

    arrival_quantiles = [
        float(ARRIVAL_MODELS[q].predict(inbound_features)[0]) for q in QUANTILES
    ]
    departure_quantiles = [
        float(DEPARTURE_MODELS[q].predict(outbound_features)[0]) for q in QUANTILES
    ]

    arr_mins = (inbound.crs_arr_time // 100) * 60 + inbound.crs_arr_time % 100
    dep_mins = (outbound.crs_dep_time // 100) * 60 + outbound.crs_dep_time % 100
    buffer = buffer_override if buffer_override is not None else dep_mins - arr_mins

    result = connection_risk(
        arrival_quantiles, departure_quantiles, QUANTILES, buffer
    )

    return {
        "miss_probability": result["miss_probability"],
        "risk_band": _risk_band(result["miss_probability"]),
        "scheduled_buffer_minutes": buffer,
        "median_time_available": result["median_time_available"],
        "p10_time_available": result["p10_time_available"],
        "p90_time_available": result["p90_time_available"],
        "inbound_arrival_delay": _forecast(arrival_quantiles),
        "outbound_departure_delay": _forecast(departure_quantiles),
        "explanation": _explain(result, buffer, arrival_quantiles),
    }