# bi_engine.py

import pandas as pd
import numpy as np
import datetime
import json
import time
from typing import Dict, Any, List, Optional
from data_processor import DataProcessor
from config import logger

class BIEngine:
    """
    Principal Business Intelligence & Analytics Engine for Monday.com.
    Executes automated semantic mapping, computes high-precision financial KPIs,
    and extracts strategic executive analytics from Deals and Work Orders datasets.
    """
    
    def __init__(self):
        self.processor = DataProcessor()
        self.deals_df: pd.DataFrame = pd.DataFrame()
        self.work_orders_df: pd.DataFrame = pd.DataFrame()

    def load_data(self) -> None:
        """
        Loads and prepares Deals and Work Orders DataFrames through the processor pipeline.
        Caches the clean dataframes locally inside the engine instance.
        """
        try:
            logger.info("BI Engine: Initiating data loading pipeline...")
            self.deals_df = self.processor.prepare_deals()
            self.work_orders_df = self.processor.prepare_work_orders()
            
            logger.info(
                f"BI Engine: Successfully loaded datasets. "
                f"Deals: {len(self.deals_df)} rows, Work Orders: {len(self.work_orders_df)} rows."
            )
        except Exception as e:
            logger.critical(f"BI Engine: Critical failure loading data: {str(e)}", exc_info=True)
            raise RuntimeError(f"BI Engine data initialization failed: {str(e)}") from e

    def _find_column(self, df: pd.DataFrame, keywords: List[str], exclude: Optional[List[str]] = None) -> Optional[str]:
        """
        Dynamically finds the best matching column name based on a list of keywords.
        """
        for col in df.columns:
            col_str = str(col).lower()
            if any(kw in col_str for kw in keywords):
                if exclude and any(ex in col_str for ex in exclude):
                    continue
                return col
        return None

    def calculate_deal_kpis(self) -> Dict[str, Any]:
        """
        Calculates Key Performance Indicators (KPIs) for the Deals Board.
        Discovers columns dynamically based on semantic signatures.
        """
        if self.deals_df.empty:
            logger.warning("Deals DataFrame is empty. Returning default Deal KPIs.")
            return {}

        df = self.deals_df
        kpis: Dict[str, Any] = {
            "total_deals": int(len(df))
        }

        # 1. Discover relevant semantic columns
        val_col = self._find_column(df, ["deal_value", "value", "amount"])
        status_col = self._find_column(df, ["deal_status", "status", "stage"])
        owner_col = self._find_column(df, ["owner", "bd_kam", "personnel"])
        prob_col = self._find_column(df, ["probability", "closure_probability"])
        created_col = self._find_column(df, ["created_date", "created"])
        close_col = self._find_column(df, ["close_date_a", "close_date"])
        tentative_close_col = self._find_column(df, ["tentative_close_date", "expected_close"])

        # 2. Pipeline value computations
        if val_col and pd.api.types.is_numeric_dtype(df[val_col]):
            non_null_vals = df[val_col].dropna()
            kpis["total_pipeline_value"] = float(non_null_vals.sum())
            kpis["average_deal_value"] = float(non_null_vals.mean()) if len(non_null_vals) > 0 else 0.0
            kpis["median_deal_value"] = float(non_null_vals.median()) if len(non_null_vals) > 0 else 0.0
            kpis["max_deal_value"] = float(non_null_vals.max()) if len(non_null_vals) > 0 else 0.0
            kpis["min_deal_value"] = float(non_null_vals.min()) if len(non_null_vals) > 0 else 0.0
        else:
            kpis["total_pipeline_value"] = 0.0
            kpis["average_deal_value"] = 0.0

        # 3. Probability analysis
        if prob_col:
            high_prob_count = df[df[prob_col].astype(str).str.lower() == "high"].shape[0]
            kpis["high_probability_deals"] = int(high_prob_count)
        else:
            kpis["high_probability_deals"] = 0

        # 4. Pipeline segments by Status
        if status_col:
            status_counts = df[status_col].fillna("Unknown").value_counts().to_dict()
            kpis["pipeline_by_status"] = {str(k): int(v) for k, v in status_counts.items()}
        else:
            kpis["pipeline_by_status"] = {}

        # 5. Deal ownership segments
        if owner_col:
            owner_counts = df[owner_col].fillna("Unassigned").value_counts().to_dict()
            kpis["deals_by_owner"] = {str(k): int(v) for k, v in owner_counts.items()}
        else:
            kpis["deals_by_owner"] = {}

        # 6. Time-series diagnostics (Target: July 2026 based on Current system time)
        target_year, target_month = 2026, 7
        
        if created_col and pd.api.types.is_datetime64_any_dtype(df[created_col]):
            created_series = df[created_col].dropna()
            this_month_created = created_series[
                (created_series.dt.year == target_year) & (created_series.dt.month == target_month)
            ]
            kpis["deals_created_this_month"] = int(len(this_month_created))
        else:
            kpis["deals_created_this_month"] = 0

        if tentative_close_col and pd.api.types.is_datetime64_any_dtype(df[tentative_close_col]):
            close_series = df[tentative_close_col].dropna()
            this_month_close = close_series[
                (close_series.dt.year == target_year) & (close_series.dt.month == target_month)
            ]
            kpis["expected_close_this_month"] = int(len(this_month_close))
        elif close_col and pd.api.types.is_datetime64_any_dtype(df[close_col]):
            close_series = df[close_col].dropna()
            this_month_close = close_series[
                (close_series.dt.year == target_year) & (close_series.dt.month == target_month)
            ]
            kpis["expected_close_this_month"] = int(len(this_month_close))
        else:
            kpis["expected_close_this_month"] = 0

        return kpis

    def calculate_work_order_kpis(self) -> Dict[str, Any]:
        """
        Calculates KPIs for the Work Orders Board.
        Dynamically registers and computes financial metrics from numerical values.
        """
        if self.work_orders_df.empty:
            logger.warning("Work Orders DataFrame is empty. Returning default WO KPIs.")
            return {}

        df = self.work_orders_df
        kpis: Dict[str, Any] = {
            "total_work_orders": int(len(df))
        }

        # 1. Discover relevant columns
        contract_col = self._find_column(df, ["amount_in_rupees_excl_of_gst_masked", "amount_excl", "contract_value"], exclude=["billed", "collected", "receivable"])
        if not contract_col:
            # Fallback to any generic masked amount
            contract_col = self._find_column(df, ["amount_in_rupees", "amount_masked"])

        billed_col = self._find_column(df, ["billed_value_in_rupees_excl_of_gst_masked", "billed_value", "billed"])
        collected_col = self._find_column(df, ["collected_amount", "collected"])
        receivable_col = self._find_column(df, ["amount_receivable_masked", "receivable"])
        status_col = self._find_column(df, ["execution_status", "wo_status_billed", "status"])

        # 2. Extract Values
        contract_val = float(df[contract_col].dropna().sum()) if contract_col and pd.api.types.is_numeric_dtype(df[contract_col]) else 0.0
        billed_val = float(df[billed_col].dropna().sum()) if billed_col and pd.api.types.is_numeric_dtype(df[billed_col]) else 0.0
        collected_val = float(df[collected_col].dropna().sum()) if collected_col and pd.api.types.is_numeric_dtype(df[collected_col]) else 0.0
        receivable_val = float(df[receivable_col].dropna().sum()) if receivable_col and pd.api.types.is_numeric_dtype(df[receivable_col]) else 0.0

        kpis["total_contract_value"] = contract_val
        kpis["total_billed"] = billed_val
        kpis["total_collected"] = collected_val
        kpis["outstanding_receivables"] = receivable_val

        # 3. Performance Rates
        kpis["billing_completion_percent"] = (billed_val / contract_val * 100) if contract_val > 0 else 0.0
        kpis["collection_efficiency"] = (collected_val / billed_val * 100) if billed_val > 0 else 0.0

        # 4. Statistical Distributions
        if contract_col and pd.api.types.is_numeric_dtype(df[contract_col]):
            kpis["average_contract_value"] = float(df[contract_col].dropna().mean()) if len(df[contract_col].dropna()) > 0 else 0.0
            kpis["largest_work_order"] = float(df[contract_col].dropna().max()) if len(df[contract_col].dropna()) > 0 else 0.0
        else:
            kpis["average_contract_value"] = 0.0
            kpis["largest_work_order"] = 0.0

        # 5. Segment breakdown
        if status_col:
            status_counts = df[status_col].fillna("Unknown").value_counts().to_dict()
            kpis["work_orders_by_status"] = {str(k): int(v) for k, v in status_counts.items()}
        else:
            kpis["work_orders_by_status"] = {}

        return kpis

    def calculate_financial_summary(self) -> Dict[str, Any]:
        """
        Extracts top-level financial metrics mapping billing gaps and leakages.
        """
        wo_kpis = self.calculate_work_order_kpis()
        if not wo_kpis:
            return {}

        contract = wo_kpis.get("total_contract_value", 0.0)
        billed = wo_kpis.get("total_billed", 0.0)
        collected = wo_kpis.get("total_collected", 0.0)
        receivables = wo_kpis.get("outstanding_receivables", 0.0)

        return {
            "revenue": contract,  # Recognized contract volume
            "billed": billed,
            "collected": collected,
            "receivables": receivables,
            "billing_gap": float(max(0.0, contract - billed)),
            "collection_gap": float(max(0.0, billed - collected))
        }

    def calculate_operational_summary(self) -> Dict[str, Any]:
        """
        Tracks progress pipelines and computes operational fulfillment percentages.
        """
        if self.work_orders_df.empty:
            return {}

        df = self.work_orders_df
        status_col = self._find_column(df, ["execution_status", "status", "wo_status"])
        
        if not status_col:
            return {
                "total_projects": len(df),
                "completed_projects": 0,
                "active_projects": 0,
                "delayed_projects": 0,
                "completion_rate": 0.0
            }

        series = df[status_col].astype(str).str.lower().fillna("unknown")
        
        completed = int(series.str.contains("completed|executed|done").sum())
        active = int(series.str.contains("ongoing|started|progress|active").sum())
        delayed = int(series.str.contains("pause|struck|delay|hold|stuck").sum())
        total = int(len(df))

        completion_rate = (completed / total * 100) if total > 0 else 0.0

        return {
            "total_projects": total,
            "completed_projects": completed,
            "active_projects": active,
            "delayed_projects": delayed,
            "completion_rate": float(completion_rate)
        }

    def calculate_executive_summary(self) -> Dict[str, Any]:
        """
        Rolls up and bundles all analytics segments into a unified executive package.
        """
        return {
            "Deals": self.calculate_deal_kpis(),
            "Work_Orders": self.calculate_work_order_kpis(),
            "Financial": self.calculate_financial_summary(),
            "Operations": self.calculate_operational_summary()
        }

    def _serialize_dict(self, d: Any) -> Any:
        """
        Recursively serializes types to native Python equivalents for JSON output.
        """
        if isinstance(d, dict):
            return {k: self._serialize_dict(v) for k, v in d.items()}
        elif isinstance(d, list):
            return [self._serialize_dict(v) for v in d]
        elif isinstance(d, (np.integer, np.int64)):
            return int(d)
        elif isinstance(d, (np.floating, np.float64)):
            return float(d) if not np.isnan(d) else None
        elif isinstance(d, (pd.Timestamp, datetime.date, datetime.datetime)):
            return d.isoformat()
        elif pd.isna(d):
            return None
        return d

    def export_summary_json(self, filename: str) -> None:
        """
        Exports the compiled executive summary to a JSON file.
        """
        try:
            logger.info(f"BI Engine: Exporting analytics summary to '{filename}'...")
            summary = self.calculate_executive_summary()
            serialized_summary = self._serialize_dict(summary)
            
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(serialized_summary, f, indent=4)
                
            logger.info("BI Engine: Export completed successfully.")
        except Exception as e:
            logger.error(f"BI Engine: Failed to export JSON summary: {str(e)}", exc_info=True)
            raise IOError(f"Failed to write BI summary JSON: {str(e)}") from e


if __name__ == "__main__":
    print("-----------------------------------")
    print("Business Intelligence Engine Test")
    print("-----------------------------------")
    
    start_time = time.time()
    try:
        engine = BIEngine()
        engine.load_data()
        
        exec_summary = engine.calculate_executive_summary()
        elapsed = time.time() - start_time
        
        print("\n[✓] Deals KPIs calculated:")
        for k, v in exec_summary["Deals"].items():
            if not isinstance(v, dict):
                print(f"  {k}: {v}")
                
        print("\n[✓] Work Order KPIs calculated:")
        for k, v in exec_summary["Work_Orders"].items():
            if not isinstance(v, dict):
                print(f"  {k}: {v}")
                
        print("\n[✓] Financial Summary calculated:")
        for k, v in exec_summary["Financial"].items():
            print(f"  {k}: {v}")
            
        print("\n[✓] Operational Summary calculated:")
        for k, v in exec_summary["Operations"].items():
            print(f"  {k}: {v}")
            
        print(f"\nExecution Time: {elapsed:.4f} seconds")
        
    except Exception as e:
        logger.error(f"Error during BI Engine testing: {str(e)}", exc_info=True)
        print(f"Python Error: {str(e)}")