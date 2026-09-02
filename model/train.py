import joblib
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from xgboost import XGBClassifier

FEATURES = [
    "inbound_arr_delay", "inbound_dep_delay", "buffer_minutes", "carrier_ontime_rate", "airport_hourly_volume", "dep_hour", "day_of_week"]
TARGET = "missed_connection"

def load_data():
    df = pd.read_parquet("data/features.parquet")
    df["fl_date"] = pd.to_datetime(df["fl_date"])
    df = df.sort_values("fl_date")

    cutoff = pd.Timestamp("2026-03-01")
    train = df[df["fl_date"] < cutoff]
    test = df[df["fl_date"] >= cutoff]

    print(f"Train: {len(train):,} rows jan - feb")
    print(f"Test:  {len(test):,} rows march")
    return train, test

def train_baseline(train, test):
    lr = LogisticRegression(max_iter=1000, class_weight="balanced")
    lr.fit(train[FEATURES], train[TARGET])

    probs = lr.predict_proba(test[FEATURES])[:, 1]
    print("\nLogistic Regression (baseline)")
    print(f"  ROC-AUC: {roc_auc_score(test[TARGET], probs):.4f}")
    print(f"  PR-AUC:  {average_precision_score(test[TARGET], probs):.4f}")
    print(f"  Brier:   {brier_score_loss(test[TARGET], probs):.4f}")
    return lr


def train_xgboost(train, test):
    neg = (train[TARGET] == 0).sum()
    pos = (train[TARGET] == 1).sum()

    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        scale_pos_weight=neg / pos,
        eval_metric="logloss",
        n_jobs=2,
    )

    model = CalibratedClassifierCV(xgb, method="isotonic", cv=3)
    model.fit(train[FEATURES], train[TARGET])

    probs = model.predict_proba(test[FEATURES])[:, 1]
    print("\nXGBoost (calibrated)")
    print(f"  ROC-AUC: {roc_auc_score(test[TARGET], probs):.4f}")
    print(f"  PR-AUC:  {average_precision_score(test[TARGET], probs):.4f}")
    print(f"  Brier:   {brier_score_loss(test[TARGET], probs):.4f}")
    return model


if __name__ == "__main__":
    train, test = load_data()
    train_baseline(train, test)
    model = train_xgboost(train, test)

    joblib.dump({"model": model, "features": FEATURES}, "model/flightguard.pkl")
    print("\nSaved model/flightguard.pkl")