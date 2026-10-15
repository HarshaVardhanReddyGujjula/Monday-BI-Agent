import sqlite3
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Any, List, Optional
from datetime import datetime, timedelta

DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "monday_bi.db"


def get_connection() -> sqlite3.Connection:
    """Creates directory and returns a connection to the SQLite database."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    """Initializes tables and seeds initial realistic sample data if empty."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        deal_name TEXT NOT NULL,
        client_name TEXT NOT NULL,
        client_tier TEXT NOT NULL,
        product_category TEXT NOT NULL,
        deal_value REAL NOT NULL,
        deal_status TEXT NOT NULL,
        probability REAL NOT NULL,
        owner TEXT NOT NULL,
        created_date TEXT NOT NULL,
        expected_close_date TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_name TEXT NOT NULL,
        client_name TEXT NOT NULL,
        contract_value REAL NOT NULL,
        billed_amount REAL NOT NULL,
        collected_amount REAL NOT NULL,
        status TEXT NOT NULL,
        completion_percent REAL NOT NULL,
        start_date TEXT NOT NULL,
        target_completion_date TEXT NOT NULL,
        billing_status TEXT NOT NULL,
        collection_status TEXT NOT NULL
    );
    """)

    cursor.execute("SELECT COUNT(*) FROM deals;")
    deals_count = cursor.fetchone()[0]

    if deals_count == 0:
        seed_sample_data(cursor)
        conn.commit()

    conn.close()


def seed_sample_data(cursor: sqlite3.Cursor) -> None:
    """Seeds realistic enterprise B2B sales and operational datasets."""
    deals_data = [
        ("Akshara Enterprise BI Rollout", "Akshara Enterprises", "Enterprise", "Enterprise BI", 4500000.0, "Closed Won", 1.0, "Harsha Reddy", "2025-11-10", "2026-01-15"),
        ("Tata Tech Data Warehouse Migration", "Tata Tech", "Enterprise", "Data Analytics", 6200000.0, "Closed Won", 1.0, "Priya Sharma", "2025-10-05", "2025-12-20"),
        ("Apex Cloud Integration Pipeline", "Apex Solutions", "Mid-Market", "Cloud Integration", 1850000.0, "Closed Won", 1.0, "Arjun Mehta", "2025-11-20", "2026-01-05"),
        ("Zenith Real-Time Analytics Portal", "Zenith Systems", "Enterprise", "Data Analytics", 5100000.0, "Negotiation", 0.85, "Harsha Reddy", "2025-12-01", "2026-02-28"),
        ("Global Logistics Fleet Telemetry", "Global Logistics", "Enterprise", "Enterprise BI", 3900000.0, "Proposal Sent", 0.70, "Kavita Nair", "2025-12-15", "2026-03-15"),
        ("Nexus Retail POS BI Pipeline", "Nexus Retail", "Mid-Market", "Enterprise BI", 1450000.0, "Closed Won", 1.0, "Priya Sharma", "2025-09-12", "2025-11-30"),
        ("HealthPlus Patient Portal Sync", "HealthPlus Ltd", "Enterprise", "Cloud Integration", 2800000.0, "Qualified", 0.60, "Arjun Mehta", "2026-01-04", "2026-04-10"),
        ("FinCore Microservices Reporting", "FinCore Capital", "Enterprise", "ERP Solutions", 7400000.0, "Negotiation", 0.80, "Harsha Reddy", "2025-11-28", "2026-03-01"),
        ("Metro Smart Meter Telemetry", "Metro Utilities", "Mid-Market", "Data Analytics", 2100000.0, "Proposal Sent", 0.50, "Kavita Nair", "2026-01-10", "2026-03-30"),
        ("Prime Logistics Route Optimizer", "Prime Cargo", "SMB", "Data Analytics", 750000.0, "Open", 0.40, "Priya Sharma", "2026-01-18", "2026-04-20"),
        ("AeroSpace Inventory Tracking", "AeroDynamics", "Enterprise", "ERP Solutions", 4800000.0, "Closed Won", 1.0, "Harsha Reddy", "2025-08-15", "2025-10-30"),
        ("OmniCommerce Sales Dashboard", "OmniCommerce", "Mid-Market", "Enterprise BI", 1200000.0, "Dead", 0.0, "Arjun Mehta", "2025-09-01", "2025-10-15"),
        ("Quantum AI Financial Ledger", "Quantum FinTech", "Enterprise", "Data Analytics", 3600000.0, "Qualified", 0.65, "Priya Sharma", "2026-01-22", "2026-04-15"),
        ("GreenGrid Renewable Energy BI", "GreenGrid Power", "Mid-Market", "Enterprise BI", 2300000.0, "Negotiation", 0.75, "Kavita Nair", "2025-12-20", "2026-03-10"),
        ("Sunrise Pharma Compliance Suite", "Sunrise Pharma", "Enterprise", "ERP Solutions", 5600000.0, "Open", 0.35, "Arjun Mehta", "2026-02-01", "2026-05-15"),
    ]

    cursor.executemany("""
    INSERT INTO deals (deal_name, client_name, client_tier, product_category, deal_value, deal_status, probability, owner, created_date, expected_close_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, deals_data)

    wo_data = [
        ("Akshara Phase 1 Dashboard Deployment", "Akshara Enterprises", 2200000.0, 2200000.0, 2000000.0, "Completed", 100.0, "2025-11-15", "2026-01-10", "Fully Billed", "Collected"),
        ("Akshara Phase 2 Integration Pipeline", "Akshara Enterprises", 2300000.0, 1500000.0, 800000.0, "Ongoing", 65.0, "2026-01-15", "2026-03-30", "Partially Billed", "Partial"),
        ("Tata Tech Data Lake Architecture", "Tata Tech", 6200000.0, 4800000.0, 3900000.0, "Ongoing", 75.0, "2025-10-10", "2026-02-28", "Partially Billed", "Partial"),
        ("Apex Cloud Migration Execution", "Apex Solutions", 1850000.0, 1850000.0, 1850000.0, "Completed", 100.0, "2025-11-25", "2026-01-05", "Fully Billed", "Collected"),
        ("Nexus Retail Analytics Store Engine", "Nexus Retail", 1450000.0, 1450000.0, 1100000.0, "Completed", 100.0, "2025-09-15", "2025-11-30", "Fully Billed", "Partial"),
        ("AeroSpace Inventory ERP Phase 1", "AeroDynamics", 4800000.0, 3200000.0, 2200000.0, "Executed until current month", 70.0, "2025-08-20", "2025-12-30", "Partially Billed", "Partial"),
        ("FinCore Microservices Reporting Core", "FinCore Capital", 3100000.0, 1200000.0, 400000.0, "Delayed / At Risk", 40.0, "2025-12-05", "2026-02-15", "Partially Billed", "Overdue"),
        ("Global Logistics Telemetry Pilot", "Global Logistics", 1500000.0, 600000.0, 300000.0, "Ongoing", 45.0, "2026-01-05", "2026-04-15", "Partially Billed", "Partial"),
    ]

    cursor.executemany("""
    INSERT INTO work_orders (order_name, client_name, contract_value, billed_amount, collected_amount, status, completion_percent, start_date, target_completion_date, billing_status, collection_status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, wo_data)


def load_database_dataframes() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Loads deals and work_orders as pandas DataFrames from SQLite."""
    init_database()
    conn = get_connection()
    deals_df = pd.read_sql_query("SELECT * FROM deals", conn)
    work_orders_df = pd.read_sql_query("SELECT * FROM work_orders", conn)
    conn.close()
    return deals_df, work_orders_df


def execute_sql(query: str) -> pd.DataFrame:
    """Executes a custom user SQL query safely on the database and returns a DataFrame."""
    init_database()
    conn = get_connection()
    try:
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()
