import pandas as pd
import numpy as np
import re
import os
from typing import Dict, Any, List, Optional, Tuple
from config import logger, MONDAY_API_KEY
from monday_client import MondayClient
import database

# Precompiled Regexes for performance optimization
RE_NON_NUMERIC_CHARS = re.compile(r"[^\d\.\-\+]")
RE_WORD_BOUNDARY = re.compile(r"[\s\-]+")
RE_NON_ALPHANUMERIC = re.compile(r"[^\w]")
RE_CONTIGUOUS_UNDERSCORES = re.compile(r"__+")

NULL_PLACEHOLDERS = {
    "", "N/A", "n/a", "N/a", "na", "NA", "-", "None", "nan", "NaN", "null", "NULL", "#VALUE!"
}


class DataProcessor:
    """
    Production-grade Data Pipeline Engine for Business Intelligence.
    Handles data ingestion from Monday.com GraphQL API, local SQLite DBMS,
    or uploaded Excel/CSV files, with automated schema normalization,
    semantic column alignment, data cleaning, and DAX measure formulation.
    """

    def __init__(self, data_source: str = "auto"):
        self.data_source = data_source
        self.monday_client: Optional[MondayClient] = None
        if MONDAY_API_KEY:
            try:
                self.monday_client = MondayClient()
            except Exception as e:
                logger.warning(f"Could not initialize MondayClient: {e}")

    def load_deals_dataframe(self) -> pd.DataFrame:
        """Fetches Deals from Monday.com API or falls back seamlessly to SQLite database."""
        if self.data_source in ("auto", "monday") and self.monday_client:
            try:
                logger.info("Attempting to fetch Deals from Monday.com API...")
                deals = self.monday_client.get_deals()
                if deals:
                    return pd.DataFrame(deals)
            except Exception as e:
                logger.warning(f"Monday API deals fetch failed ({e}). Falling back to SQLite.")

        # Fallback to local SQLite relational database
        logger.info("Loading Deals from SQLite database (database.py)...")
        deals_df, _ = database.load_database_dataframes()
        return deals_df

    def load_work_orders_dataframe(self) -> pd.DataFrame:
        """Fetches Work Orders from Monday.com API or falls back seamlessly to SQLite database."""
        if self.data_source in ("auto", "monday") and self.monday_client:
            try:
                logger.info("Attempting to fetch Work Orders from Monday.com API...")
                work_orders = self.monday_client.get_work_orders()
                if work_orders:
                    return pd.DataFrame(work_orders)
            except Exception as e:
                logger.warning(f"Monday API work orders fetch failed ({e}). Falling back to SQLite.")

        # Fallback to local SQLite relational database
        logger.info("Loading Work Orders from SQLite database (database.py)...")
        _, wo_df = database.load_database_dataframes()
        return wo_df

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Removes duplicates, trims whitespaces, and replaces empty placeholders with None."""
        if df.empty:
            return df

        df_clean = df.copy()
        df_clean = df_clean.drop_duplicates()
        df_clean.columns = [str(col).strip() for col in df_clean.columns]

        for col in df_clean.columns:
            series = df_clean[col]
            if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
                continue

            stripped = series.astype(str).str.strip()
            stripped = stripped.where(series.notna(), None)
            is_placeholder = stripped.isin(NULL_PLACEHOLDERS)
            df_clean[col] = stripped.mask(is_placeholder, None)

        return df_clean

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Converts column names to lowercase snake_case for standardized BI processing."""
        if df.empty:
            return df

        clean_cols = []
        for col in df.columns:
            norm = str(col).lower().strip()
            norm = RE_WORD_BOUNDARY.sub("_", norm)
            norm = RE_NON_ALPHANUMERIC.sub("", norm)
            norm = RE_CONTIGUOUS_UNDERSCORES.sub("_", norm).strip("_")
            clean_cols.append(norm if norm else f"col_{len(clean_cols)}")

        counts = {}
        unique_cols = []
        for col in clean_cols:
            if col in counts:
                counts[col] += 1
                unique_cols.append(f"{col}_{counts[col]}")
            else:
                counts[col] = 0
                unique_cols.append(col)

        df_renamed = df.copy()
        df_renamed.columns = unique_cols
        return df_renamed

    def standardize_semantic_columns(self, df: pd.DataFrame, is_deals: bool) -> pd.DataFrame:
        """Maps diverse API and board column names to unified canonical names."""
        if df.empty:
            return df

        df = df.copy()
        cols = {c: c.lower() for c in df.columns}

        def find_match(keywords: List[str], exclude: Optional[List[str]] = None) -> Optional[str]:
            for orig, low in cols.items():
                if any(k in low for k in keywords):
                    if exclude and any(e in low for e in exclude):
                        continue
                    return orig
            return None

        if is_deals:
            val = find_match(["deal_value", "masked_deal_value", "value", "amount"])
            status = find_match(["deal_status", "status", "stage", "deal_stage"])
            owner = find_match(["owner_code", "owner", "bd_kam"])
            client = find_match(["client_code", "client_name", "client", "customer"])
            prob = find_match(["closure_probability", "probability", "prob"])
            created = find_match(["created_date", "created", "date"])
            cat = find_match(["product_deal", "product_category", "product", "sector"])

            mapping = {}
            if val and val != "deal_value": mapping[val] = "deal_value"
            if status and status != "deal_status": mapping[status] = "deal_status"
            if owner and owner != "owner": mapping[owner] = "owner"
            if client and client != "client_name": mapping[client] = "client_name"
            if prob and prob != "probability": mapping[prob] = "probability"
            if created and created != "created_date": mapping[created] = "created_date"
            if cat and cat != "product_category": mapping[cat] = "product_category"

            if mapping:
                df = df.rename(columns=mapping)

            if "client_tier" not in df.columns and "deal_value" in df.columns:
                val_num = pd.to_numeric(df["deal_value"], errors="coerce").fillna(0.0)
                df["client_tier"] = pd.cut(
                    val_num,
                    bins=[-1, 1000000, 3000000, float("inf")],
                    labels=["SMB (< 1M)", "Mid-Market (1M - 3M)", "Enterprise (> 3M)"]
                ).astype(str)

        else: # Work Orders
            cv = find_match(["contract_value", "amount_in_rupees", "amount", "value"], exclude=["billed", "collected", "receivable"])
            billed = find_match(["billed_value", "billed_amount", "billed"])
            collected = find_match(["collected_amount", "collected", "receipt"])
            status = find_match(["execution_status", "wo_status", "status"])
            client = find_match(["customer_name", "client_name", "client", "customer"])
            comp = find_match(["completion_percent", "completion", "progress"])

            mapping = {}
            if cv and cv != "contract_value": mapping[cv] = "contract_value"
            if billed and billed != "billed_amount": mapping[billed] = "billed_amount"
            if collected and collected != "collected_amount": mapping[collected] = "collected_amount"
            if status and status != "status": mapping[status] = "status"
            if client and client != "client_name": mapping[client] = "client_name"
            if comp and comp != "completion_percent": mapping[comp] = "completion_percent"

            if mapping:
                df = df.rename(columns=mapping)

        return df

    def convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detects and converts currency and numeric strings into floats."""
        if df.empty:
            return df

        df_num = df.copy()
        for col in df_num.columns:
            series = df_num[col]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            if pd.api.types.is_numeric_dtype(series):
                continue

            non_null = series.dropna()
            if len(non_null) == 0:
                continue

            cleaned_series = non_null.astype(str).str.replace(RE_NON_NUMERIC_CHARS, "", regex=True)
            numeric_parsed = pd.to_numeric(cleaned_series, errors="coerce")
            valid_pct = numeric_parsed.notna().sum() / len(non_null)

            if valid_pct >= 0.7:
                df_num[col] = pd.to_numeric(
                    series.astype(str).str.replace(RE_NON_NUMERIC_CHARS, "", regex=True),
                    errors="coerce"
                )

        return df_num

    def convert_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detects date keywords or formats and converts columns to pandas datetime."""
        if df.empty:
            return df

        df_date = df.copy()
        date_keywords = ["date", "time", "created", "close", "start", "target", "deadline"]

        for col in df_date.columns:
            col_str = str(col).lower()
            if any(k in col_str for k in date_keywords):
                try:
                    df_date[col] = pd.to_datetime(df_date[col], errors="coerce")
                except Exception:
                    pass

        return df_date

    def apply_dax_business_measures(self, deals_df: pd.DataFrame, wo_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Formulates custom DAX-equivalent analytical business measures:
        - Deals: weighted_value, deal_size_tier
        - Work Orders: billing_gap, collection_gap, collection_efficiency_pct, billing_realization_pct
        """
        if not deals_df.empty:
            val_col = "deal_value" if "deal_value" in deals_df.columns else None
            prob_col = "probability" if "probability" in deals_df.columns else None

            if val_col and prob_col:
                prob_numeric = pd.to_numeric(deals_df[prob_col], errors="coerce").fillna(0.5)
                prob_numeric = prob_numeric.apply(lambda x: x / 100.0 if x > 1.0 else x)
                deals_df["weighted_value"] = pd.to_numeric(deals_df[val_col], errors="coerce").fillna(0.0) * prob_numeric
            elif val_col:
                deals_df["weighted_value"] = pd.to_numeric(deals_df[val_col], errors="coerce").fillna(0.0)

            if val_col:
                val_num = pd.to_numeric(deals_df[val_col], errors="coerce").fillna(0.0)
                deals_df["deal_size_tier"] = pd.cut(
                    val_num,
                    bins=[-1, 1000000, 3000000, float("inf")],
                    labels=["SMB (< 1M)", "Mid-Market (1M - 3M)", "Enterprise (> 3M)"]
                ).astype(str)

        if not wo_df.empty:
            cv = pd.to_numeric(wo_df["contract_value"], errors="coerce").fillna(0.0) if "contract_value" in wo_df.columns else pd.Series(0.0, index=wo_df.index)
            billed = pd.to_numeric(wo_df["billed_amount"], errors="coerce").fillna(0.0) if "billed_amount" in wo_df.columns else pd.Series(0.0, index=wo_df.index)
            collected = pd.to_numeric(wo_df["collected_amount"], errors="coerce").fillna(0.0) if "collected_amount" in wo_df.columns else pd.Series(0.0, index=wo_df.index)

            wo_df["billing_gap"] = cv - billed
            wo_df["collection_gap"] = billed - collected
            wo_df["collection_efficiency_pct"] = (collected / billed.replace(0, np.nan) * 100.0).fillna(0.0)
            wo_df["billing_realization_pct"] = (billed / cv.replace(0, np.nan) * 100.0).fillna(0.0)

        return deals_df, wo_df

    def prepare_deals(self) -> pd.DataFrame:
        """Executes full data cleaning, normalization, semantic mapping, and measure formulation for Deals."""
        df = self.load_deals_dataframe()
        if df.empty:
            return df
        df = self.clean_dataframe(df)
        df = self.normalize_column_names(df)
        df = self.standardize_semantic_columns(df, is_deals=True)
        df = self.convert_numeric_columns(df)
        df = self.convert_date_columns(df)
        return df

    def prepare_work_orders(self) -> pd.DataFrame:
        """Executes full data cleaning, normalization, semantic mapping, and measure formulation for Work Orders."""
        df = self.load_work_orders_dataframe()
        if df.empty:
            return df
        df = self.clean_dataframe(df)
        df = self.normalize_column_names(df)
        df = self.standardize_semantic_columns(df, is_deals=False)
        df = self.convert_numeric_columns(df)
        df = self.convert_date_columns(df)
        return df

    def get_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generates comprehensive data profiling & health statistics for Business Analysts."""
        if df.empty:
            return {"row_count": 0, "column_count": 0, "missing_values": {}, "numeric_columns": []}

        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])],
            "date_columns": [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        }