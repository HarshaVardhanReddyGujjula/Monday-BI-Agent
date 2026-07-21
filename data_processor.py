import pandas as pd
import numpy as np
import re
import time
import sys
from typing import Dict, Any, List, Optional
from monday_client import MondayClient
from config import logger

# Precompiled Regexes for performance optimization
RE_NON_NUMERIC_CHARS = re.compile(r"[^\d\.\-\+]")
RE_WORD_BOUNDARY = re.compile(r"[\s\-]+")
RE_NON_ALPHANUMERIC = re.compile(r"[^\w]")
RE_CONTIGUOUS_UNDERSCORES = re.compile(r"__+")

# Standard placeholders to treat as Null / NaN
NULL_PLACEHOLDERS = {
    "", "N/A", "n/a", "N/a", "na", "NA", "-", "None", "nan", "NaN", "null", "NULL", "#VALUE!"
}

class DataProcessor:
    """
    Production-grade Data Pipeline Engine for Monday.com BI.
    Provides robust, dynamic cleaning, schema-normalization, high-precision semantic type inference,
    and memory-optimized dataset generation.
    """
    
    def __init__(self):
        self.client = MondayClient()

    def load_deals_dataframe(self) -> pd.DataFrame:
        """
        Fetches Deals data from the MondayClient and loads it into a Pandas DataFrame.
        """
        try:
            logger.info("Loading Deals raw data into DataFrame...")
            deals = self.client.get_deals()
            if not deals:
                logger.warning("No Deals retrieved from the Monday API.")
                return pd.DataFrame()
            return pd.DataFrame(deals)
        except Exception as e:
            logger.error(f"Error loading Deals dataframe: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to load Deals dataframe: {str(e)}") from e

    def load_work_orders_dataframe(self) -> pd.DataFrame:
        """
        Fetches Work Orders data from the MondayClient and loads it into a Pandas DataFrame.
        """
        try:
            logger.info("Loading Work Orders raw data into DataFrame...")
            work_orders = self.client.get_work_orders()
            if not work_orders:
                logger.warning("No Work Orders retrieved from the Monday API.")
                return pd.DataFrame()
            return pd.DataFrame(work_orders)
        except Exception as e:
            logger.error(f"Error loading Work Orders dataframe: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to load Work Orders dataframe: {str(e)}") from e

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Performs high-quality diagnostic cleaning on the DataFrame.
        Removes duplicates, strips strings, replaces empty elements or placeholders with None,
        and preserves already parsed numeric or date datatypes.
        """
        if df.empty:
            return df
            
        logger.info("Cleaning dataframe: removing duplicates and trimming whitespaces...")
        df_clean = df.copy(deep=False)  # Minimize memory copy until required
        
        # 1. Remove duplicate rows
        df_clean = df_clean.drop_duplicates()
        
        # 2. Strip whitespace from column names
        df_clean.columns = [str(col).strip() for col in df_clean.columns]
        
        # 3. Clean string columns using vectorized operations
        for col in df_clean.columns:
            series = df_clean[col]
            if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
                continue
                
            # Perform vectorized string conversion and stripping
            stripped_series = series.astype(str).str.strip()
            stripped_series = stripped_series.where(series.notna(), None)
            
            # Map placeholders to None
            is_placeholder = stripped_series.isin(NULL_PLACEHOLDERS)
            df_clean[col] = stripped_series.mask(is_placeholder, None)
            
        return df_clean

    def normalize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Converts column names to lowercase, replaces spaces/hyphens with underscores,
        and strips all non-alphanumeric characters (except underscores).
        """
        if df.empty:
            return df
            
        logger.info("Normalizing column names...")
        df_norm = df.copy(deep=False)
        normalized_cols = []
        
        for col in df_norm.columns:
            col_str = str(col).lower().strip()
            col_under = RE_WORD_BOUNDARY.sub("_", col_str)
            col_clean = RE_NON_ALPHANUMERIC.sub("", col_under)
            col_clean = RE_CONTIGUOUS_UNDERSCORES.sub("_", col_clean)
            normalized_cols.append(col_clean)
            
        df_norm.columns = normalized_cols
        return df_norm

    def _score_numeric_confidence(self, col_name: str, series: pd.Series) -> float:
        """
        Calculates a confidence score (0.0 to 1.0) for a column being numeric.
        """
        col_lower = col_name.lower()
        
        # Categorical indicators and textual column markers
        categorical_indicators = {"status", "code", "name", "text", "description", "category", "type", "nature", "priority"}
        is_categorical_name = any(cat in col_lower for cat in categorical_indicators)
        is_id_name = "id" in col_lower or "serial" in col_lower or "invoice" in col_lower or "no" in col_lower
        
        non_null_vals = series.dropna()
        if len(non_null_vals) == 0:
            return 0.0
            
        # Sample up to 100 values for high efficiency
        sample_vals = non_null_vals.sample(n=min(100, len(non_null_vals)), random_state=42)
        
        # For ID, Serial, Invoice, Code, etc, we strictly require all sampled values to be clean digits
        if is_id_name or is_categorical_name:
            all_digits = all(str(v).strip().isdigit() for v in sample_vals)
            return 1.0 if all_digits else 0.0
            
        # Standard numeric detection confidence checking
        numeric_count = 0
        has_currency = False
        has_percent = False
        
        for val in sample_vals:
            val_str = str(val).strip()
            if not val_str or val_str in NULL_PLACEHOLDERS:
                continue
            
            if "₹" in val_str or "$" in val_str or "rs" in val_str.lower():
                has_currency = True
            if "%" in val_str:
                has_percent = True
                
            cleaned = RE_NON_NUMERIC_CHARS.sub("", val_str)
            try:
                float(cleaned)
                numeric_count += 1
            except ValueError:
                pass
                
        pct_numeric = numeric_count / len(sample_vals)
        
        # Currency/percent booster
        if (has_currency or has_percent) and pct_numeric > 0.5:
            return 1.0
            
        numeric_hints = {
            "value", "amount", "rupees", "gst", "billed", "collected", "receivable", 
            "quantity", "quantities", "balance", "probability", "rate", "price", 
            "count", "sum", "percent", "val"
        }
        has_hint = any(hint in col_lower for hint in numeric_hints)
        
        if has_hint and pct_numeric > 0.5:
            return 0.9
        elif pct_numeric > 0.8:
            return 0.8
            
        return 0.0

    def convert_numeric_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Automatically detects numeric columns using a confidence scoring system,
        and converts them to float or integer, replacing non-numeric values with NaN.
        """
        if df.empty:
            return df
            
        logger.info("Automatically detecting and converting numeric columns...")
        df_num = df.copy(deep=False)
        
        for col in df_num.columns:
            if pd.api.types.is_numeric_dtype(df_num[col]):
                continue
                
            confidence = self._score_numeric_confidence(col, df_num[col])
            
            if confidence >= 0.8:
                def parse_number(v: Any) -> Optional[float]:
                    if v is None or pd.isna(v):
                        return np.nan
                    v_str = str(v).strip()
                    if not v_str or v_str in NULL_PLACEHOLDERS:
                        return np.nan
                    cleaned = RE_NON_NUMERIC_CHARS.sub("", v_str)
                    try:
                        return float(cleaned) if cleaned else np.nan
                    except ValueError:
                        return np.nan
                
                # Apply parser and cast
                parsed_series = df_num[col].apply(parse_number)
                df_num[col] = pd.to_numeric(parsed_series, errors='coerce')
                
                # Dynamic Integer vs Float determination
                non_nan_vals = df_num[col].dropna()
                if len(non_nan_vals) > 0 and all(val.is_integer() for val in non_nan_vals):
                    try:
                        df_num[col] = df_num[col].astype('Int64')
                        logger.info(f"Column '{col}' dynamically cast as Int64 (Nullable Integer)")
                    except Exception:
                        pass
                
                logger.info(f"Successfully converted column '{col}' to numeric with confidence {confidence:.2f}")
                
        return df_num

    def _score_date_confidence(self, col_name: str, series: pd.Series) -> bool:
        """
        Determines if a column should be converted to date based on strict rules:
        - at least 80% of sampled values parse as valid dates
        - AND the column name strongly suggests a date
        - AND never convert invoice numbers, serial numbers, quantities, codes, or IDs
        """
        col_lower = col_name.lower()
        
        excluded_keywords = {
            "invoice_no", "invoice_number", "serial", "quantity", "quantities", 
            "code", "id", "priority", "balance", "value", "collected", "billed"
        }
        if any(word in col_lower for word in excluded_keywords):
            return False
            
        date_hints = {
            "date", "month", "time", "updated", "created", "closed", "expected", 
            "actual", "delivery", "start", "end", "latest", "executed", "close"
        }
        has_date_hint = any(hint in col_lower for hint in date_hints)
        if not has_date_hint:
            return False
            
        non_null_vals = series.dropna()
        if len(non_null_vals) == 0:
            return False
            
        # Sample up to 100 values
        sample_vals = non_null_vals.sample(n=min(100, len(non_null_vals)), random_state=42)
        
        valid_date_count = 0
        for val in sample_vals:
            val_str = str(val).strip()
            if not val_str or val_str in NULL_PLACEHOLDERS:
                continue
                
            # Avoid small numbers or simple integers that can falsely parse as UNIX timestamps
            if val_str.isdigit() and len(val_str) < 8:
                continue
                
            try:
                pd.to_datetime(val_str, errors='raise')
                valid_date_count += 1
            except Exception:
                pass
                
        pct_dates = valid_date_count / len(sample_vals) if len(sample_vals) > 0 else 0
        return pct_dates >= 0.8

    def convert_date_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Automatically detects and converts date columns using strict confidence thresholds
        while avoiding false positives in structural keys.
        """
        if df.empty:
            return df
            
        logger.info("Automatically detecting and converting date columns...")
        df_date = df.copy(deep=False)
        
        for col in df_date.columns:
            if pd.api.types.is_datetime64_any_dtype(df_date[col]):
                continue
                
            should_convert = self._score_date_confidence(col, df_date[col])
            
            if should_convert:
                try:
                    df_date[col] = pd.to_datetime(df_date[col], errors='coerce', format='mixed')
                    logger.info(f"Successfully converted column '{col}' to datetime (mixed format).")
                except Exception:
                    df_date[col] = pd.to_datetime(df_date[col], errors='coerce')
                    logger.info(f"Successfully converted column '{col}' to datetime (fallback format).")
                    
        return df_date

    def get_summary_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generates clean profiling metadata for a given dataframe.
        """
        if df.empty:
            return {
                "row_count": 0,
                "column_count": 0,
                "missing_values": {},
                "duplicate_rows": 0,
                "numeric_columns": [],
                "date_columns": []
            }
            
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        date_cols = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]
        
        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "missing_values": df.isnull().sum().to_dict(),
            "duplicate_rows": int(df.duplicated().sum()),
            "numeric_columns": numeric_cols,
            "date_columns": date_cols
        }

    def prepare_deals(self) -> pd.DataFrame:
        """
        Executes the complete pipeline for loading, cleaning, and validating Deals.
        """
        logger.info("Running complete pipeline for Deals...")
        df = self.load_deals_dataframe()
        if df.empty:
            return df
            
        df = self.clean_dataframe(df)
        df = self.normalize_column_names(df)
        df = self.convert_numeric_columns(df)
        df = self.convert_date_columns(df)
        return df

    def prepare_work_orders(self) -> pd.DataFrame:
        """
        Executes the complete pipeline for loading, cleaning, and validating Work Orders.
        """
        logger.info("Running complete pipeline for Work Orders...")
        df = self.load_work_orders_dataframe()
        if df.empty:
            return df
            
        df = self.clean_dataframe(df)
        df = self.normalize_column_names(df)
        df = self.convert_numeric_columns(df)
        df = self.convert_date_columns(df)
        return df


if __name__ == "__main__":
    print("-----------------------------------")
    print("Data Processor Test")
    print("-----------------------------------")
    
    start_time = time.time()
    try:
        processor = DataProcessor()
        
        deals_df = processor.prepare_deals()
        work_orders_df = processor.prepare_work_orders()
        elapsed_time = time.time() - start_time
        
        print(f"Deals Shape: {deals_df.shape}")
        print(f"Work Orders Shape: {work_orders_df.shape}")
        print(f"Execution Time: {elapsed_time:.4f} seconds")
        
        # Numeric Columns
        deals_num = [col for col in deals_df.columns if pd.api.types.is_numeric_dtype(deals_df[col])]
        wo_num = [col for col in work_orders_df.columns if pd.api.types.is_numeric_dtype(work_orders_df[col])]
        print(f"Numeric Columns (Deals): {deals_num}")
        print(f"Numeric Columns (Work Orders): {wo_num}")
        
        # Date Columns
        deals_date = [col for col in deals_df.columns if pd.api.types.is_datetime64_any_dtype(deals_df[col])]
        wo_date = [col for col in work_orders_df.columns if pd.api.types.is_datetime64_any_dtype(work_orders_df[col])]
        print(f"Date Columns (Deals): {deals_date}")
        print(f"Date Columns (Work Orders): {wo_date}")
        
        # Memory Usage
        deals_mem = deals_df.memory_usage(deep=True).sum() / 1024
        wo_mem = work_orders_df.memory_usage(deep=True).sum() / 1024
        print(f"Deals Memory Usage: {deals_mem:.2f} KB")
        print(f"Work Orders Memory Usage: {wo_mem:.2f} KB")
        
        if not deals_df.empty:
            print("\nDeals Summary Statistics:")
            stats = processor.get_summary_statistics(deals_df)
            for k, v in stats.items():
                if k != "missing_values":
                    print(f"  {k}: {v}")
                    
        if not work_orders_df.empty:
            print("\nWork Orders Summary Statistics:")
            stats = processor.get_summary_statistics(work_orders_df)
            for k, v in stats.items():
                if k != "missing_values":
                    print(f"  {k}: {v}")
                    
    except Exception as e:
        logger.error(f"Error during Data Processor testing: {str(e)}", exc_info=True)
        print(f"Python Error: {str(e)}")
        sys.exit(1)