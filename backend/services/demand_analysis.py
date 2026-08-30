"""
NITK Campus Mobility - Demand Analysis Module.
Provides analytical methods, temporal breakdowns, and metric calculations
for synthetic ride-request simulation datasets.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

DEFAULT_REQUESTS_PATH = Path(__file__).resolve().parent.parent / "data" / "ride_requests.csv"
DEFAULT_DIST_MATRIX_PATH = Path(__file__).resolve().parent.parent / "data" / "distance_matrix.csv"
DEFAULT_TIME_MATRIX_PATH = Path(__file__).resolve().parent.parent / "data" / "travel_time_matrix.csv"


class DemandAnalyzer:
    """Analytical utility for evaluating synthetic ride demand characteristics."""

    def __init__(
        self,
        requests_df: Optional[pd.DataFrame] = None,
        requests_path: Optional[Path] = None,
        dist_matrix_path: Optional[Path] = None,
        time_matrix_path: Optional[Path] = None,
    ) -> None:
        if requests_df is not None:
            self.df = requests_df.copy()
        else:
            p = requests_path or DEFAULT_REQUESTS_PATH
            if not p.exists():
                raise FileNotFoundError(f"Requests file not found at: {p}")
            self.df = pd.read_csv(p)

        # Load distance and time lookups
        self.dist_matrix_path = dist_matrix_path or DEFAULT_DIST_MATRIX_PATH
        self.time_matrix_path = time_matrix_path or DEFAULT_TIME_MATRIX_PATH
        self.dist_lookup: Dict[Tuple[str, str], float] = self._load_matrix(self.dist_matrix_path, "distance_km")
        self.time_lookup: Dict[Tuple[str, str], float] = self._load_matrix(self.time_matrix_path, "travel_time_min")

    def _load_matrix(self, path: Path, val_col: str) -> Dict[Tuple[str, str], float]:
        """Loads OD pair values into a dictionary lookup."""
        lookup = {}
        if path.exists():
            with open(path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    lookup[(row["origin_id"], row["destination_id"])] = float(row[val_col])
        return lookup

    def get_requests_per_hour(self) -> Dict[str, int]:
        """Returns request counts grouped by hour of the day."""
        hours = self.df["request_time"].apply(lambda t: t.split(":")[0] + ":00")
        counts = hours.value_counts().sort_index().to_dict()
        return counts

    def get_requests_per_time_period(self) -> Dict[str, int]:
        """Classifies requests into the 7 standard diurnal periods."""
        def classify_period(time_str: str) -> str:
            h, m = map(int, time_str.split(":"))
            total_m = h * 60 + m
            if 300 <= total_m < 420:
                return "05:00-07:00 (Early Morning)"
            elif 420 <= total_m < 600:
                return "07:00-10:00 (Morning Peak)"
            elif 600 <= total_m < 720:
                return "10:00-12:00 (Mid-Day)"
            elif 720 <= total_m < 870:
                return "12:00-14:30 (Lunch Peak)"
            elif 870 <= total_m < 1020:
                return "14:30-17:00 (Afternoon)"
            elif 1020 <= total_m < 1200:
                return "17:00-20:00 (Evening Peak)"
            else:
                return "20:00-23:00 (Night)"

        periods = self.df["request_time"].apply(classify_period)
        return periods.value_counts().to_dict()

    def get_requests_by_origin(self, top_n: int = 10) -> Dict[str, int]:
        """Returns top origin location IDs by request count."""
        return self.df["origin_id"].value_counts().head(top_n).to_dict()

    def get_requests_by_destination(self, top_n: int = 10) -> Dict[str, int]:
        """Returns top destination location IDs by request count."""
        return self.df["destination_id"].value_counts().head(top_n).to_dict()

    def get_requests_by_request_type(self) -> Dict[str, int]:
        """Returns count of requests by user type (student, staff, faculty)."""
        return self.df["request_type"].value_counts().to_dict()

    def get_requests_by_passenger_count(self) -> Dict[int, int]:
        """Returns distribution of passenger counts (1–4)."""
        return {int(k): int(v) for k, v in self.df["passenger_count"].value_counts().sort_index().items()}

    def get_average_trip_distance(self) -> float:
        """Calculates average shortest-path distance (km) across all requests."""
        if not self.dist_lookup:
            return 0.0
        dists = [
            self.dist_lookup.get((row["origin_id"], row["destination_id"]), 0.0)
            for _, row in self.df.iterrows()
        ]
        return round(float(sum(dists) / max(len(dists), 1)), 3)

    def get_average_trip_time(self) -> float:
        """Calculates average shortest-path travel time (minutes) across all requests."""
        if not self.time_lookup:
            return 0.0
        times = [
            self.time_lookup.get((row["origin_id"], row["destination_id"]), 0.0)
            for _, row in self.df.iterrows()
        ]
        return round(float(sum(times) / max(len(times), 1)), 2)

    def get_peak_demand_location(self) -> Tuple[str, int]:
        """Identifies location with the highest combined origin+destination demand."""
        combined = pd.concat([self.df["origin_id"], self.df["destination_id"]])
        top_loc = combined.value_counts().index[0]
        top_count = int(combined.value_counts().iloc[0])
        return top_loc, top_count

    def get_peak_demand_period(self) -> Tuple[str, int]:
        """Identifies diurnal time period with the highest request volume."""
        period_counts = self.get_requests_per_time_period()
        top_period = max(period_counts.items(), key=lambda x: x[1])
        return top_period[0], top_period[1]

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generates comprehensive analytical summary metrics."""
        num_requests = len(self.df)
        num_days = self.df["request_date"].nunique()
        reqs_per_day = round(num_requests / max(num_days, 1), 1)
        avg_passengers = round(float(self.df["passenger_count"].mean()), 2)
        avg_dist = self.get_average_trip_distance()
        avg_time = self.get_average_trip_time()
        
        peak_loc, peak_loc_count = self.get_peak_demand_location()
        peak_period, peak_period_count = self.get_peak_demand_period()

        hourly = self.get_requests_per_hour()
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0]

        return {
            "total_requests": num_requests,
            "simulation_days": num_days,
            "requests_per_day": reqs_per_day,
            "average_passengers": avg_passengers,
            "average_trip_distance_km": avg_dist,
            "average_trip_time_min": avg_time,
            "peak_hour": peak_hour,
            "peak_demand_period": peak_period,
            "peak_location": peak_loc,
            "top_origins": self.get_requests_by_origin(10),
            "top_destinations": self.get_requests_by_destination(10),
            "request_type_distribution": self.get_requests_by_request_type(),
            "passenger_count_distribution": self.get_requests_by_passenger_count(),
        }
