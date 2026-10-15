import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from data_processor import DataProcessor
from config import logger


class BIEngine:
    """
    Principal Business Intelligence & Analytics Engine.
    Computes high-precision financial KPIs, DAX-equivalent measures,
    time-series revenue trends, customer segmentations, and dynamic filtered views.
    """

    def __init__(self, data_source: str = "auto"):
        self.processor = DataProcessor(data_source=data_source)
        self.deals_df: pd.DataFrame = pd.DataFrame()
        self.work_orders_df: pd.DataFrame = pd.DataFrame()
        self.filtered_deals_df: pd.DataFrame = pd.DataFrame()
        self.filtered_wo_df: pd.DataFrame = pd.DataFrame()

    def load_data(self) -> None:
        """Loads and cleans datasets, then calculates initial DAX-style measures."""
        try:
            logger.info("BI Engine: Loading datasets...")
            raw_deals = self.processor.prepare_deals()
            raw_wo = self.processor.prepare_work_orders()

            self.deals_df, self.work_orders_df = self.processor.apply_dax_business_measures(
                raw_deals, raw_wo
            )
            self.filtered_deals_df = self.deals_df.copy()
            self.filtered_wo_df = self.work_orders_df.copy()

            logger.info(
                f"BI Engine: Successfully loaded datasets. "
                f"Deals: {len(self.deals_df)} rows, Work Orders: {len(self.work_orders_df)} rows."
            )
        except Exception as e:
            logger.error(f"BI Engine: Failed to load data: {e}", exc_info=True)
            raise

    def apply_filters(
        self,
        date_range: Optional[Tuple[Any, Any]] = None,
        deal_statuses: Optional[List[str]] = None,
        owners: Optional[List[str]] = None,
        client_tiers: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        wo_statuses: Optional[List[str]] = None
    ) -> None:
        """Applies dynamic multi-dimensional dashboard slicers across both datasets."""
        d_df = self.deals_df.copy()
        w_df = self.work_orders_df.copy()

        # Filter Deals
        if not d_df.empty:
            if deal_statuses and "deal_status" in d_df.columns:
                d_df = d_df[d_df["deal_status"].isin(deal_statuses)]

            if owners and "owner" in d_df.columns:
                d_df = d_df[d_df["owner"].isin(owners)]

            if client_tiers and "client_tier" in d_df.columns:
                d_df = d_df[d_df["client_tier"].isin(client_tiers)]

            if categories and "product_category" in d_df.columns:
                d_df = d_df[d_df["product_category"].isin(categories)]

            if date_range and len(date_range) == 2 and "created_date" in d_df.columns:
                start_dt, end_dt = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
                if pd.notna(start_dt) and pd.notna(end_dt):
                    d_df = d_df[(d_df["created_date"] >= start_dt) & (d_df["created_date"] <= end_dt)]

        # Filter Work Orders
        if not w_df.empty:
            if wo_statuses and "status" in w_df.columns:
                w_df = w_df[w_df["status"].isin(wo_statuses)]

        self.filtered_deals_df = d_df
        self.filtered_wo_df = w_df

    def calculate_deal_kpis(self) -> Dict[str, Any]:
        """Calculates comprehensive sales pipeline and deal KPIs."""
        df = self.filtered_deals_df
        if df.empty:
            return {
                "total_deals": 0, "total_pipeline_value": 0.0, "weighted_pipeline_value": 0.0,
                "average_deal_value": 0.0, "win_rate_pct": 0.0, "high_probability_deals": 0,
                "pipeline_by_status": {}, "deals_by_owner": {}, "deals_by_tier": {},
                "deals_by_category": {}, "monthly_trends": {}
            }

        val_col = "deal_value" if "deal_value" in df.columns else None
        status_col = "deal_status" if "deal_status" in df.columns else None
        owner_col = "owner" if "owner" in df.columns else None
        tier_col = "client_tier" if "client_tier" in df.columns else None
        cat_col = "product_category" if "product_category" in df.columns else None
        weighted_col = "weighted_value" if "weighted_value" in df.columns else None
        date_col = "created_date" if "created_date" in df.columns else None

        total_deals = len(df)
        total_val = float(df[val_col].fillna(0).sum()) if val_col else 0.0
        weighted_val = float(df[weighted_col].fillna(0).sum()) if weighted_col else total_val * 0.65
        avg_val = total_val / total_deals if total_deals > 0 else 0.0

        # Win Rate Calculation
        win_rate = 0.0
        if status_col:
            statuses = df[status_col].astype(str).str.lower()
            won_count = statuses[statuses.str.contains("won")].count()
            lost_count = statuses[statuses.str.contains("lost|dead")].count()
            closed_total = won_count + lost_count
            win_rate = (won_count / closed_total * 100.0) if closed_total > 0 else (won_count / total_deals * 100.0)

        # High Probability Deals (prob >= 0.70)
        prob_col = "probability" if "probability" in df.columns else None
        high_prob_count = 0
        if prob_col:
            prob_num = pd.to_numeric(df[prob_col], errors="coerce").fillna(0)
            prob_num = prob_num.apply(lambda x: x / 100.0 if x > 1.0 else x)
            high_prob_count = int((prob_num >= 0.70).sum())

        # Monthly Trends for Revenue / Deals
        monthly_trends = {}
        if date_col and val_col and pd.api.types.is_datetime64_any_dtype(df[date_col]):
            temp_df = df.dropna(subset=[date_col]).copy()
            temp_df["year_month"] = temp_df[date_col].dt.strftime("%Y-%m")
            grouped = temp_df.groupby("year_month")[val_col].agg(["sum", "count"]).reset_index()
            grouped = grouped.sort_values("year_month")
            monthly_trends = {
                row["year_month"]: {"revenue": float(row["sum"]), "count": int(row["count"])}
                for _, row in grouped.iterrows()
            }

        return {
            "total_deals": total_deals,
            "total_pipeline_value": total_val,
            "weighted_pipeline_value": weighted_val,
            "average_deal_value": avg_val,
            "win_rate_pct": win_rate,
            "high_probability_deals": high_prob_count,
            "pipeline_by_status": df[status_col].value_counts().to_dict() if status_col else {},
            "deals_by_owner": df[owner_col].value_counts().to_dict() if owner_col else {},
            "deals_by_tier": df[tier_col].value_counts().to_dict() if tier_col else {},
            "deals_by_category": df[cat_col].value_counts().to_dict() if cat_col else {},
            "monthly_trends": monthly_trends
        }

    def calculate_work_order_kpis(self) -> Dict[str, Any]:
        """Calculates project execution, billing, and operational KPIs."""
        df = self.filtered_wo_df
        if df.empty:
            return {
                "total_work_orders": 0, "total_contract_value": 0.0, "total_billed": 0.0,
                "total_collected": 0.0, "outstanding_receivables": 0.0, "billing_completion_percent": 0.0,
                "collection_efficiency": 0.0, "work_orders_by_status": {}, "average_contract_value": 0.0
            }

        cv = float(df["contract_value"].fillna(0).sum()) if "contract_value" in df.columns else 0.0
        billed = float(df["billed_amount"].fillna(0).sum()) if "billed_amount" in df.columns else 0.0
        collected = float(df["collected_amount"].fillna(0).sum()) if "collected_amount" in df.columns else 0.0
        receivables = billed - collected

        billing_comp = (billed / cv * 100.0) if cv > 0 else 0.0
        coll_eff = (collected / billed * 100.0) if billed > 0 else 0.0
        status_counts = df["status"].value_counts().to_dict() if "status" in df.columns else {}

        return {
            "total_work_orders": len(df),
            "total_contract_value": cv,
            "total_billed": billed,
            "total_collected": collected,
            "outstanding_receivables": receivables,
            "billing_completion_percent": billing_comp,
            "collection_efficiency": coll_eff,
            "average_contract_value": cv / len(df) if len(df) > 0 else 0.0,
            "work_orders_by_status": status_counts
        }

    def calculate_financial_summary(self) -> Dict[str, Any]:
        """Computes executive cash-flow leakage and balance metrics."""
        wo = self.calculate_work_order_kpis()
        rev = wo.get("total_contract_value", 0.0)
        billed = wo.get("total_billed", 0.0)
        collected = wo.get("total_collected", 0.0)
        rec = wo.get("outstanding_receivables", 0.0)

        return {
            "revenue": rev,
            "billed": billed,
            "collected": collected,
            "receivables": rec,
            "billing_gap": max(0.0, rev - billed),
            "collection_gap": max(0.0, billed - collected),
            "realization_rate": (collected / rev * 100.0) if rev > 0 else 0.0
        }

    def calculate_operations_summary(self) -> Dict[str, Any]:
        """Computes operational progress, completion rates, and delay alerts."""
        df = self.filtered_wo_df
        if df.empty:
            return {"total_projects": 0, "completed_projects": 0, "active_projects": 0, "delayed_projects": 0, "completion_rate": 0.0}

        total = len(df)
        status_col = df["status"].astype(str).str.lower() if "status" in df.columns else pd.Series([])

        completed = int(status_col[status_col.str.contains("completed")].count())
        delayed = int(status_col[status_col.str.contains("delay|risk|pause|struck")].count())
        active = total - completed - delayed

        comp_pct = df["completion_percent"].mean() if "completion_percent" in df.columns else (completed / total * 100.0 if total > 0 else 0.0)

        return {
            "total_projects": total,
            "completed_projects": completed,
            "active_projects": max(0, active),
            "delayed_projects": delayed,
            "completion_rate": float(comp_pct)
        }

    def calculate_executive_summary(self) -> Dict[str, Any]:
        """Consolidates all modular summaries into a single executive dashboard payload."""
        return {
            "Deals": self.calculate_deal_kpis(),
            "Work_Orders": self.calculate_work_order_kpis(),
            "Financial": self.calculate_financial_summary(),
            "Operations": self.calculate_operations_summary()
        }