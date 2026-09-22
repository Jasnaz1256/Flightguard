import joblib
import pandas as pd

from sklearn.metrics import mean_absolute_error
from xgboost import XGBRegressor

CATEGORICAL = ['carrier', 'origin', 'dest', 'route']

NUMERIC = ['dep_hour', 'day_of_week', 'month', 'leg_number', 'scheduled_turnaround',
           'carrier_avg_delay', 'route_avg_delay', 'origin_avg_delay', 'origin_hourly_volume',]

QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]

def load_data():
    df = pd.read_parquet('data/flight_features.parquet')
    df['fl_date'] = pd.to_datetime(df['fl_date'])

    encoders = {}
    for col in CATEGORICAL:
        categories = df[col].astype('category').cat.categories
        encoders[col] = {value: i for i, value in enumerate(categories)}
        df[col + '_enc'] = df[col].map(encoders[col]).fillna(-1).astype(int)

    cuttoff = pd.Timestamp("2026-03-01")
    train = df[df['fl_date'] < cuttoff]
    test = df[df['fl_date'] >= cuttoff]

    print(f"Train: {len(train):,} flights jan-feb")
    print(f"Test: {len(test):,} flights mar")
    return train, test, encoders

def train_quantiles(train, test, target, label):
    features = NUMERIC + [c + "_enc" for c in CATEGORICAL]

    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]

    models = {}
    print(f"\n[{label}] Training {len(QUANTILES)} quantile regression models")

    for q in QUANTILES:
        model = XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=q,
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            n_jobs=2,
        )
        model.fit(X_train, y_train)
        models[q] = model

        preds = model.predict(X_test)
        coverage = (y_test <= preds).mean()
        print(f"  q={q:<5} coverage {coverage:.3f} (target {q})")

    median_preds = models[0.5].predict(X_test)
    print(f"  Median MAE: {mean_absolute_error(y_test, median_preds):.2f} minutes")

    return models, features


def inspect_predictions(test, models, features, target, n=15):
    """Show predicted quantiles alongside actual outcomes for a sample of flights."""
    sample = test.sample(n, random_state=42)
    X = sample[features]

    out = pd.DataFrame({
        "carrier": sample["carrier"].values,
        "route": sample["route"].values,
        "hour": sample["dep_hour"].values,
        "actual": sample[target].values,
    })
    for q in QUANTILES:
        out[f"q{int(q * 100)}"] = models[q].predict(X).round(1)

    out["in_range"] = (out["actual"] >= out["q10"]) & (out["actual"] <= out["q90"])

    print(f"\nSample predictions for {target}:")
    print(out.to_string(index=False))
    print(f"Actual within predicted 10-90 range: {out['in_range'].mean():.0%}")



if __name__ == "__main__":
    train, test, encoders = load_data()

    arr_models, features = train_quantiles(train, test, "arr_delay", "arrival")
    inspect_predictions(test, arr_models, features, "arr_delay")
    dep_models, _ = train_quantiles(train, test, "dep_delay", "departure")

    joblib.dump(
        {
            "arrival_models": arr_models,
            "departure_models": dep_models,
            "features": features,
            "encoders": encoders,
            "quantiles": QUANTILES,
        },
        "model/flightguard_delay.pkl",
    )
    print("\nSaved model/flightguard_delay.pkl")
