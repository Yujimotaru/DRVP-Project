from pathlib import Path
import pandas as pd
import numpy as np


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "backend" / "data"


def load_data():
    """Load Phase 3 ride requests and Phase 1 locations."""

    requests_path = DATA_DIR / "ride_requests.csv"
    locations_path = DATA_DIR / "locations.csv"

    requests = pd.read_csv(requests_path)
    locations = pd.read_csv(locations_path)

    return requests, locations


def prepare_requests():
    """
    Clean and enrich the synthetic ride-request dataset.
    """

    requests, locations = load_data()

    requests["datetime"] = pd.to_datetime(
        requests["request_date"].astype(str)
        + " "
        + requests["request_time"].astype(str)
    )

    requests = requests.sort_values("datetime").reset_index(drop=True)

    requests["date"] = requests["datetime"].dt.date
    requests["hour"] = requests["datetime"].dt.hour
    requests["minute"] = requests["datetime"].dt.minute
    requests["day_of_week"] = requests["datetime"].dt.dayofweek

    requests["is_weekend"] = (
        requests["day_of_week"] >= 5
    ).astype(int)

    requests["time_bucket"] = (
        requests["datetime"].dt.floor("15min")
    )

    origin_info = locations[
        [
            "location_id",
            "type",
            "campus",
            "morning_demand_weight",
            "lunch_demand_weight",
            "evening_demand_weight",
            "night_demand_weight",
        ]
    ].copy()

    origin_info = origin_info.rename(
        columns={
            "location_id": "origin_id",
            "type": "origin_type",
            "campus": "origin_campus",
            "morning_demand_weight": "origin_morning_weight",
            "lunch_demand_weight": "origin_lunch_weight",
            "evening_demand_weight": "origin_evening_weight",
            "night_demand_weight": "origin_night_weight",
        }
    )

    requests = requests.merge(
        origin_info,
        on="origin_id",
        how="left",
    )

    return requests


def aggregate_demand():
    """
    Aggregate requests into 15-minute location-level demand.

    IMPORTANT:
    A complete location x time grid is created so that
    intervals with zero requests are represented explicitly.
    """

    requests = prepare_requests()

    grouped = (
        requests.groupby(
            [
                "time_bucket",
                "origin_id",
            ],
            as_index=False,
        )
        .size()
        .rename(columns={"size": "request_count"})
    )

    # --------------------------------------------------
    # Create complete 15-minute time range
    # --------------------------------------------------

    min_time = requests["time_bucket"].min()
    max_time = requests["time_bucket"].max()

    all_times = pd.date_range(
        start=min_time,
        end=max_time,
        freq="15min",
    )

    all_locations = requests[
        "origin_id"
    ].drop_duplicates().sort_values()

    complete_index = pd.MultiIndex.from_product(
        [
            all_times,
            all_locations,
        ],
        names=[
            "time_bucket",
            "origin_id",
        ],
    )

    complete = (
        grouped
        .set_index(
            [
                "time_bucket",
                "origin_id",
            ]
        )
        .reindex(complete_index, fill_value=0)
        .reset_index()
    )

    # --------------------------------------------------
    # Attach location information
    # --------------------------------------------------

    locations = load_data()[1]

    origin_info = locations[
        [
            "location_id",
            "type",
            "campus",
            "morning_demand_weight",
            "lunch_demand_weight",
            "evening_demand_weight",
            "night_demand_weight",
        ]
    ].copy()

    origin_info = origin_info.rename(
        columns={
            "location_id": "origin_id",
            "type": "origin_type",
            "campus": "origin_campus",
            "morning_demand_weight": "origin_morning_weight",
            "lunch_demand_weight": "origin_lunch_weight",
            "evening_demand_weight": "origin_evening_weight",
            "night_demand_weight": "origin_night_weight",
        }
    )

    complete = complete.merge(
        origin_info,
        on="origin_id",
        how="left",
    )

    complete["request_count"] = (
        complete["request_count"]
        .astype(int)
    )

    return complete


def add_time_features(df):
    """Add temporal features."""

    df = df.copy()

    df["time_bucket"] = pd.to_datetime(
        df["time_bucket"]
    )

    df["date"] = (
        df["time_bucket"].dt.date
    )

    df["hour"] = (
        df["time_bucket"].dt.hour
    )

    df["minute"] = (
        df["time_bucket"].dt.minute
    )

    df["day_of_week"] = (
        df["time_bucket"].dt.dayofweek
    )

    df["is_weekend"] = (
        df["day_of_week"] >= 5
    ).astype(int)

    minutes_since_midnight = (
        df["hour"] * 60
        + df["minute"]
    )

    df["time_sin"] = np.sin(
        2
        * np.pi
        * minutes_since_midnight
        / 1440
    )

    df["time_cos"] = np.cos(
        2
        * np.pi
        * minutes_since_midnight
        / 1440
    )

    return df


def add_lag_features(df):
    """
    Create true time-based historical demand features.

    All lag and rolling features use ONLY past demand.
    """

    df = df.copy()

    df["time_bucket"] = pd.to_datetime(
        df["time_bucket"]
    )

    df = df.sort_values(
        [
            "origin_id",
            "time_bucket",
        ]
    ).reset_index(drop=True)

    grouped = df.groupby(
        "origin_id",
        group_keys=False,
    )

    # --------------------------------------------------
    # TRUE TIME LAGS
    # --------------------------------------------------

    df["lag_15min"] = grouped[
        "request_count"
    ].shift(1)

    df["lag_30min"] = grouped[
        "request_count"
    ].shift(2)

    df["lag_60min"] = grouped[
        "request_count"
    ].shift(4)

    df["lag_1day"] = grouped[
        "request_count"
    ].shift(96)

    # --------------------------------------------------
    # TRUE HISTORICAL ROLLING WINDOWS
    # --------------------------------------------------

    df["rolling_1hour"] = (
        grouped["request_count"]
        .transform(
            lambda x:
            x.shift(1)
            .rolling(
                window=4,
                min_periods=1,
            )
            .mean()
        )
    )

    df["rolling_4hour"] = (
        grouped["request_count"]
        .transform(
            lambda x:
            x.shift(1)
            .rolling(
                window=16,
                min_periods=1,
            )
            .mean()
        )
    )

    return df


def build_feature_dataset():
    """
    Build final Phase 4 feature dataset.
    """

    df = aggregate_demand()

    df = add_time_features(df)

    df = add_lag_features(df)

    lag_columns = [
        "lag_15min",
        "lag_30min",
        "lag_60min",
        "lag_1day",
        "rolling_1hour",
        "rolling_4hour",
    ]

    for column in lag_columns:
        df[column] = (
            df[column]
            .fillna(0)
        )

    return df


if __name__ == "__main__":

    df = build_feature_dataset()

    print(
        "Phase 4 feature engineering successful."
    )

    print(
        f"Rows: {len(df)}"
    )

    print(
        f"Columns: {len(df.columns)}"
    )

    print("\nColumns:")

    for column in df.columns:
        print(f"- {column}")

    print("\nTime range:")

    print(
        f"{df['time_bucket'].min()} "
        f"to "
        f"{df['time_bucket'].max()}"
    )

    print("\nUnique locations:")

    print(
        df["origin_id"].nunique()
    )

    print("\nZero-demand rows:")

    print(
        int(
            (df["request_count"] == 0)
            .sum()
        )
    )

    print("\nSample:")

    print(
        df.head(10).to_string(
            index=False
        )
    )