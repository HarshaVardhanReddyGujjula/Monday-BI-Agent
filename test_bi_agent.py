import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from bi_engine import BIEngine
from ai_assistant import BusinessAssistant
import database

def test_pipeline():
    print("=== Testing Database Initialization & Seeding ===")
    database.init_database()
    deals_df, wo_df = database.load_database_dataframes()
    print(f"Deals in DB: {len(deals_df)}, Work Orders in DB: {len(wo_df)}")
    assert len(deals_df) > 0, "Deals table should not be empty!"
    assert len(wo_df) > 0, "Work Orders table should not be empty!"

    print("\n=== Testing SQL Execution ===")
    sql_res = database.execute_sql("SELECT count(*) as count FROM deals")
    print("SQL Count Result:", sql_res.to_dict())

    print("\n=== Testing BI Engine & Measure Formulation ===")
    engine = BIEngine(data_source="auto")
    engine.load_data()
    summary = engine.calculate_executive_summary()
    
    deals_kpis = summary["Deals"]
    wo_kpis = summary["Work_Orders"]
    fin = summary["Financial"]
    ops = summary["Operations"]

    print("Pipeline Value:", deals_kpis["total_pipeline_value"])
    print("Weighted Pipeline Value:", deals_kpis["weighted_pipeline_value"])
    print("Win Rate %:", deals_kpis["win_rate_pct"])
    print("Contract Revenue:", fin["revenue"])
    print("Collected Cash:", fin["collected"])
    print("Collection Efficiency %:", wo_kpis["collection_efficiency"])
    print("Billing Gap:", fin["billing_gap"])
    print("Delayed Projects:", ops["delayed_projects"])

    assert deals_kpis["total_pipeline_value"] > 0
    assert fin["revenue"] > 0

    print("\n=== Testing Slicers / Filters ===")
    engine.apply_filters(deal_statuses=["Closed Won"])
    filtered_summary = engine.calculate_executive_summary()
    print("Filtered Won Deals:", filtered_summary["Deals"]["total_deals"])

    print("\n=== Testing AI Business Assistant (Offline Reasoning Engine) ===")
    assistant = BusinessAssistant(summary=summary)
    ans1 = assistant.ask("Which projects are delayed?")
    print("\nAI Response (Delayed Projects):\n", ans1)

    ans2 = assistant.ask("What is our collection gap and efficiency?")
    print("\nAI Response (Collection Gap):\n", ans2)

    print("\n=== ALL INTEGRATION TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    test_pipeline()
