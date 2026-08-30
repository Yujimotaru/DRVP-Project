"""
NITK Campus Mobility - Synthetic Demand Generator.
Generates reproducible, realistic diurnal ride-request simulation datasets
mapped to the 54-location NITK mobility graph and Phase 1 demand weights.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np

from backend.services.location_service import LocationService
from backend.services.campus_graph_service import CampusGraphService

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "data" / "demand_generation_config.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "ride_requests.csv"


class DemandGenerator:
    """Service for generating synthetic campus ride requests."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        location_service: Optional[LocationService] = None,
        graph_service: Optional[CampusGraphService] = None,
    ) -> None:
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.location_service = location_service or LocationService()
        self.graph_service = graph_service or CampusGraphService()
        
        self.config = self._load_config()
        self.locations = self.location_service.get_all_locations()
        self.locations_by_id = {loc.location_id: loc for loc in self.locations}
        self.locations_by_type = self._group_locations_by_type()

    def _load_config(self) -> Dict[str, Any]:
        """Loads generation configuration from JSON."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at: {self.config_path}")
        with open(self.config_path, mode="r", encoding="utf-8") as f:
            return json.load(f)

    def _group_locations_by_type(self) -> Dict[str, List[Any]]:
        """Groups location objects by their functional category."""
        grouped: Dict[str, List[Any]] = {}
        for loc in self.locations:
            grouped.setdefault(loc.type, []).append(loc)
        return grouped

    def _get_category_locations(self, category_key: str) -> List[Any]:
        """Maps flow categories to location lists."""
        cat = category_key.lower().strip()
        if cat in {"hostel", "hostels"}:
            return self.locations_by_type.get("hostel_boys", []) + self.locations_by_type.get("hostel_girls", [])
        elif cat in {"academic", "academics"}:
            return (
                self.locations_by_type.get("department", [])
                + self.locations_by_type.get("lecture_hall", [])
                + self.locations_by_type.get("library", [])
            )
        elif cat in {"lecture_hall", "lecture_halls"}:
            return self.locations_by_type.get("lecture_hall", [])
        elif cat in {"department", "departments"}:
            return self.locations_by_type.get("department", [])
        elif cat in {"library", "libraries"}:
            return self.locations_by_type.get("library", [])
        elif cat in {"mess", "messes"}:
            return self.locations_by_type.get("mess", [])
        elif cat in {"suprabha", "canteen", "canteens"}:
            return self.locations_by_type.get("canteen", [])
        elif cat in {"coop", "cooperative_society", "cooperative_societies"}:
            return self.locations_by_type.get("cooperative_society", [])
        elif cat in {"gate", "gates"}:
            return self.locations_by_type.get("gate", [])
        return self.locations

    def _sample_location(
        self,
        candidate_locs: List[Any],
        weight_col: str,
        rng: np.random.Generator,
        exclude_id: Optional[str] = None,
    ) -> Any:
        """Samples a location weighted by demand weights and capacity."""
        valid_candidates = [loc for loc in candidate_locs if loc.location_id != exclude_id]
        if not valid_candidates:
            valid_candidates = [loc for loc in self.locations if loc.location_id != exclude_id]

        weights = []
        for loc in valid_candidates:
            base_w = getattr(loc, weight_col, 0.5)
            cap_w = max(loc.capacity, 10) ** 0.2
            weights.append(max(base_w * cap_w, 0.01))

        probs = np.array(weights) / sum(weights)
        selected_idx = rng.choice(len(valid_candidates), p=probs)
        return valid_candidates[selected_idx]

    def _parse_time_range(self, start_str: str, end_str: str) -> Tuple[int, int]:
        """Converts HH:MM strings to start and end minutes from midnight."""
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        return sh * 60 + sm, eh * 60 + em

    def generate_requests_for_time_window(
        self,
        date_str: str,
        period_dict: Dict[str, Any],
        count: int,
        rng: np.random.Generator,
        start_request_idx: int = 1,
    ) -> List[Dict[str, Any]]:
        """Generates synthetic requests for a specific time window."""
        requests = []
        start_min, end_min = self._parse_time_range(period_dict["start_time"], period_dict["end_time"])
        weight_col = period_dict["weight_column"]
        flow_prefs = period_dict.get("flow_preferences", {"general": 1.0})

        flow_keys = list(flow_prefs.keys())
        flow_probs = np.array(list(flow_prefs.values()), dtype=float)
        flow_probs /= flow_probs.sum()

        req_types = list(self.config["request_type_distribution"].keys())
        req_type_probs = list(self.config["request_type_distribution"].values())

        p_counts = [int(k) for k in self.config["passenger_count_distribution"].keys()]
        p_count_probs = list(self.config["passenger_count_distribution"].values())

        priorities = list(self.config["priority_distribution"].keys())
        priority_probs = list(self.config["priority_distribution"].values())

        date_compact = date_str.replace("-", "")

        for i in range(count):
            req_idx = start_request_idx + i
            req_id = f"req_{date_compact}_{req_idx:04d}"

            # Pick flow preference
            chosen_flow = rng.choice(flow_keys, p=flow_probs)
            if "_to_" in chosen_flow:
                orig_cat, dest_cat = chosen_flow.split("_to_")
                orig_pool = self._get_category_locations(orig_cat)
                dest_pool = self._get_category_locations(dest_cat)
            else:
                orig_pool = self.locations
                dest_pool = self.locations

            # Sample origin and destination ensuring origin != destination
            orig_loc = self._sample_location(orig_pool, weight_col, rng)
            dest_loc = self._sample_location(dest_pool, weight_col, rng, exclude_id=orig_loc.location_id)

            # Sample time uniformly within window
            minute_of_day = rng.integers(start_min, end_min)
            req_time_str = f"{minute_of_day // 60:02d}:{minute_of_day % 60:02d}"

            # Attributes
            req_type = rng.choice(req_types, p=req_type_probs)
            passengers = int(rng.choice(p_counts, p=p_count_probs))
            prio = rng.choice(priorities, p=priority_probs)

            # Wait tolerance
            wait_bounds = self.config["max_wait_minutes"][prio]
            max_wait = round(float(rng.uniform(wait_bounds["min"], wait_bounds["max"])), 1)

            requests.append({
                "request_id": req_id,
                "request_date": date_str,
                "request_time": req_time_str,
                "origin_id": orig_loc.location_id,
                "destination_id": dest_loc.location_id,
                "passenger_count": passengers,
                "request_type": req_type,
                "priority": prio,
                "max_wait_min": max_wait,
                "status": "pending",
            })

        return requests

    def generate_daily_requests(
        self,
        date: str = "2026-09-01",
        seed: Optional[int] = None,
        base_requests: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generates all requests for a single simulation day with reproducible seed."""
        rng = np.random.default_rng(seed)
        total_target = base_requests or self.config["simulation_defaults"]["base_requests_per_day"]
        
        # Add slight daily variation (~ +/- 10%)
        daily_count = int(rng.normal(total_target, total_target * 0.08))
        daily_count = max(daily_count, 50)

        all_daily_requests = []
        req_counter = 1

        for period in self.config["time_periods"]:
            period_rate = period["relative_rate"]
            period_count = int(round(daily_count * period_rate))
            period_count = max(period_count, 1)

            period_reqs = self.generate_requests_for_time_window(
                date_str=date,
                period_dict=period,
                count=period_count,
                rng=rng,
                start_request_idx=req_counter,
            )
            all_daily_requests.extend(period_reqs)
            req_counter += len(period_reqs)

        # Sort chronologically by request_time
        all_daily_requests.sort(key=lambda r: r["request_time"])
        return all_daily_requests

    def generate_requests(
        self,
        start_date: Optional[str] = None,
        num_days: Optional[int] = None,
        seed: Optional[int] = None,
        base_requests_per_day: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Generates a complete multi-day synthetic dataset."""
        s_date_str = start_date or self.config["simulation_defaults"]["start_date"]
        days = num_days or self.config["simulation_defaults"]["num_days"]
        base_seed = seed if seed is not None else self.config["simulation_defaults"]["default_seed"]
        base_rate = base_requests_per_day or self.config["simulation_defaults"]["base_requests_per_day"]

        start_dt = datetime.strptime(s_date_str, "%Y-%m-%d")
        all_requests = []

        for d in range(days):
            current_date = (start_dt + timedelta(days=d)).strftime("%Y-%m-%d")
            day_seed = base_seed + d * 1000 if base_seed is not None else None
            day_requests = self.generate_daily_requests(
                date=current_date,
                seed=day_seed,
                base_requests=base_rate,
            )
            all_requests.extend(day_requests)

        return all_requests

    def save_requests(
        self,
        requests: List[Dict[str, Any]],
        file_path: Optional[Path] = None,
    ) -> Path:
        """Saves generated requests to CSV."""
        out_path = file_path or DEFAULT_OUTPUT_PATH
        out_path.parent.mkdir(parents=True, exist_ok=True)

        fieldnames = [
            "request_id",
            "request_date",
            "request_time",
            "origin_id",
            "destination_id",
            "passenger_count",
            "request_type",
            "priority",
            "max_wait_min",
            "status",
        ]

        with open(out_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(requests)

        return out_path


# Global helpers
def generate_daily_requests(
    date: str = "2026-09-01",
    seed: Optional[int] = None,
    base_requests: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Convenience helper to generate single-day requests."""
    return DemandGenerator().generate_daily_requests(date, seed, base_requests)


def generate_requests(
    start_date: str = "2026-09-01",
    num_days: int = 30,
    seed: int = 42,
    base_requests_per_day: int = 170,
) -> List[Dict[str, Any]]:
    """Convenience helper to generate multi-day requests."""
    return DemandGenerator().generate_requests(start_date, num_days, seed, base_requests_per_day)
