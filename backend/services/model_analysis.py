"""
NITK Campus Mobility - Model Analysis & Evaluation Module.
Calculates residual errors, temporal/spatial accuracy breakdowns,
and feature importance rankings for the demand forecasting model.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd

from backend.services.demand_model import DemandPredictionModel

DEFAULT_ANALYSIS_DIR = Path(__file__).resolve().parent.parent / "data" / "analysis"


class ModelAnalyzer:
    """Analytical utility for evaluating demand model performance and feature dynamics."""

    def __init__(
        self,
        model: Optional[DemandPredictionModel] = None,
        test_df: Optional[pd.DataFrame] = None,
        predictions_df: Optional[pd.DataFrame] = None,
    ) -> None:
        self.model = model or DemandPredictionModel()
        self.test_df = test_df
        self.predictions_df = predictions_df

    def get_actual_vs_predicted_summary(self, eval_df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates core regression metrics across evaluation partition."""
        return self.model.evaluate(eval_df)

    def get_error_by_hour(self, eval_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Breaks down MAE and RMSE across hours of the day."""
        cat_cols = self.model.config["features"]["categorical"]
        num_cols = self.model.config["features"]["numeric"]
        X_eval = eval_df[cat_cols + num_cols]
        preds = np.clip(self.model.pipeline.predict(X_eval), 0.0, None)

        eval_copy = eval_df.copy()
        eval_copy["pred"] = preds
        eval_copy["abs_err"] = np.abs(eval_copy["request_count"] - eval_copy["pred"])
        eval_copy["sq_err"] = (eval_copy["request_count"] - eval_copy["pred"]) ** 2

        hourly = {}
        for h, grp in eval_copy.groupby("hour"):
            h_str = f"{h:02d}:00"
            hourly[h_str] = {
                "mae": round(float(grp["abs_err"].mean()), 4),
                "rmse": round(float(np.sqrt(grp["sq_err"].mean())), 4),
                "actual_sum": int(grp["request_count"].sum()),
                "pred_sum": round(float(grp["pred"].sum()), 1),
            }
        return hourly

    def get_error_by_location_type(self, eval_df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
        """Breaks down prediction error across functional location types."""
        cat_cols = self.model.config["features"]["categorical"]
        num_cols = self.model.config["features"]["numeric"]
        X_eval = eval_df[cat_cols + num_cols]
        preds = np.clip(self.model.pipeline.predict(X_eval), 0.0, None)

        eval_copy = eval_df.copy()
        eval_copy["pred"] = preds
        eval_copy["abs_err"] = np.abs(eval_copy["request_count"] - eval_copy["pred"])
        eval_copy["sq_err"] = (eval_copy["request_count"] - eval_copy["pred"]) ** 2

        type_metrics = {}
        for l_type, grp in eval_copy.groupby("location_type"):
            type_metrics[l_type] = {
                "mae": round(float(grp["abs_err"].mean()), 4),
                "rmse": round(float(np.sqrt(grp["sq_err"].mean())), 4),
                "actual_count": int(grp["request_count"].sum()),
                "predicted_count": round(float(grp["pred"].sum()), 1),
            }
        return type_metrics

    def get_top_features(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Returns top N most influential features by Gini importance."""
        return self.model.get_feature_importances()[:top_n]
