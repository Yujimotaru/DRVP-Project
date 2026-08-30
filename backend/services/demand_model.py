from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .demand_features import build_feature_dataset


BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "backend" / "models"
DATA_DIR = BASE_DIR / "backend" / "data"

MODEL_DIR.mkdir(parents=True, exist_ok=True)


MODEL_PATH = MODEL_DIR / "demand_model.pkl"
CONFIG_PATH = DATA_DIR / "demand_model_config.json"
PREDICTIONS_PATH = DATA_DIR / "demand_predictions.csv"


TARGET = "request_count"


FEATURES = [
    "origin_id",
    "origin_type",
    "origin_campus",
    "origin_morning_weight",
    "origin_lunch_weight",
    "origin_evening_weight",
    "origin_night_weight",
    "hour",
    "minute",
    "day_of_week",
    "is_weekend",
    "time_sin",
    "time_cos",
    "lag_15min",
    "lag_30min",
    "lag_60min",
    "lag_1day",
    "rolling_1hour",
    "rolling_4hour",
]


def encode_features(df):
    """
    Convert categorical features into numerical columns.

    The returned dataframe contains only model-compatible numeric data.
    """

    encoded = df.copy()

    encoded = pd.get_dummies(
        encoded,
        columns=["origin_id", "origin_type", "origin_campus"],
        dtype=int,
    )

    return encoded


def chronological_split(df):
    """
    Split the dataset chronologically.

    70% training
    15% validation
    15% test
    """

    df = df.sort_values("time_bucket").reset_index(drop=True)

    n = len(df)

    train_end = int(n * 0.70)
    validation_end = int(n * 0.85)

    train = df.iloc[:train_end].copy()
    validation = df.iloc[train_end:validation_end].copy()
    test = df.iloc[validation_end:].copy()

    return train, validation, test


def prepare_model_data(df):
    """
    Prepare X and y for the Random Forest model.
    """

    encoded = encode_features(df)

    feature_columns = [
        column
        for column in encoded.columns
        if column in FEATURES
        or column.startswith("origin_id_")
        or column.startswith("origin_type_")
        or column.startswith("origin_campus_")
    ]

    X = encoded[feature_columns].copy()
    y = encoded[TARGET].copy()

    return X, y, feature_columns


def calculate_metrics(actual, predicted):
    """Calculate standard regression metrics."""

    rmse = np.sqrt(
        mean_squared_error(actual, predicted)
    )

    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(rmse),
        "r2": float(r2_score(actual, predicted)),
    }


def baseline_prediction(train, test):
    """
    Baseline prediction.

    Uses the average historical demand for each location.

    Only training data is used to calculate the averages.
    """

    location_means = (
        train.groupby("origin_id")[TARGET]
        .mean()
    )

    global_mean = train[TARGET].mean()

    predictions = test["origin_id"].map(
        location_means
    )

    predictions = predictions.fillna(global_mean)

    return predictions.to_numpy()


def train_model():
    """
    Train and evaluate the Phase 4 demand model.
    """

    print("Loading Phase 4 feature dataset...")

    df = build_feature_dataset()

    print(f"Total feature rows: {len(df)}")

    train, validation, test = chronological_split(df)

    print(f"Training rows: {len(train)}")
    print(f"Validation rows: {len(validation)}")
    print(f"Test rows: {len(test)}")

    X_train, y_train, feature_columns = prepare_model_data(
        train
    )

    X_validation, y_validation, _ = prepare_model_data(
        validation
    )

    X_test, y_test, _ = prepare_model_data(
        test
    )

    # Make sure validation/test have exactly the same
    # feature columns as training.
    X_validation = X_validation.reindex(
        columns=X_train.columns,
        fill_value=0,
    )

    X_test = X_test.reindex(
        columns=X_train.columns,
        fill_value=0,
    )

    print(f"Number of model features: {len(X_train.columns)}")

    # --------------------------------------------------
    # BASELINE
    # --------------------------------------------------

    baseline_pred = baseline_prediction(
        train,
        test,
    )

    baseline_metrics = calculate_metrics(
        y_test,
        baseline_pred,
    )

    # --------------------------------------------------
    # RANDOM FOREST
    # --------------------------------------------------

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=18,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )

    print("Training Random Forest...")

    model.fit(
        X_train,
        y_train,
    )

    validation_pred = model.predict(
        X_validation
    )

    test_pred = model.predict(
        X_test
    )

    # Demand cannot be negative.
    validation_pred = np.maximum(
        validation_pred,
        0,
    )

    test_pred = np.maximum(
        test_pred,
        0,
    )

    validation_metrics = calculate_metrics(
        y_validation,
        validation_pred,
    )

    test_metrics = calculate_metrics(
        y_test,
        test_pred,
    )

    # --------------------------------------------------
    # SAVE MODEL
    # --------------------------------------------------

    artifact = {
        "model": model,
        "feature_columns": list(X_train.columns),
        "model_version": "phase4-random-forest-v1",
    }

    joblib.dump(
        artifact,
        MODEL_PATH,
    )

    print(f"Model saved: {MODEL_PATH}")

    # --------------------------------------------------
    # FEATURE IMPORTANCE
    # --------------------------------------------------

    importances = pd.Series(
        model.feature_importances_,
        index=X_train.columns,
    ).sort_values(
        ascending=False
    )

    print("\nTop 10 features:")

    for feature, importance in importances.head(10).items():
        print(
            f"- {feature}: {importance:.6f}"
        )

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------

    print("\nBASELINE METRICS")
    print(f"MAE:  {baseline_metrics['mae']:.4f}")
    print(f"RMSE: {baseline_metrics['rmse']:.4f}")
    print(f"R2:   {baseline_metrics['r2']:.4f}")

    print("\nRANDOM FOREST VALIDATION METRICS")
    print(f"MAE:  {validation_metrics['mae']:.4f}")
    print(f"RMSE: {validation_metrics['rmse']:.4f}")
    print(f"R2:   {validation_metrics['r2']:.4f}")

    print("\nRANDOM FOREST TEST METRICS")
    print(f"MAE:  {test_metrics['mae']:.4f}")
    print(f"RMSE: {test_metrics['rmse']:.4f}")
    print(f"R2:   {test_metrics['r2']:.4f}")

    # --------------------------------------------------
    # PREDICTIONS
    # --------------------------------------------------

    predictions = test[
        [
            "time_bucket",
            "origin_id",
        ]
    ].copy()

    predictions["actual_demand"] = (
        y_test.to_numpy()
    )

    predictions["predicted_demand"] = (
        test_pred
    )

    predictions["predicted_demand"] = (
        predictions["predicted_demand"]
        .round(2)
    )

    predictions["model_version"] = (
        "phase4-random-forest-v1"
    )

    predictions.to_csv(
        PREDICTIONS_PATH,
        index=False,
    )

    print(
        f"\nPredictions saved: {PREDICTIONS_PATH}"
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    summary = {
        "total_rows": len(df),
        "training_rows": len(train),
        "validation_rows": len(validation),
        "test_rows": len(test),
        "feature_count": len(X_train.columns),
        "model": "RandomForestRegressor",
        "model_version": "phase4-random-forest-v1",
        "baseline": baseline_metrics,
        "validation": validation_metrics,
        "test": test_metrics,
        "mean_actual_test_demand": float(
            y_test.mean()
        ),
        "mean_predicted_test_demand": float(
            np.mean(test_pred)
        ),
        "max_actual_test_demand": float(
            y_test.max()
        ),
        "max_predicted_test_demand": float(
            np.max(test_pred)
        ),
    }

    with open(
        DATA_DIR / "demand_model_results.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            summary,
            f,
            indent=2,
        )

    print(
        "\nPhase 4 model training complete."
    )


if __name__ == "__main__":
    train_model()