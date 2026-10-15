# 📊 Monday BI Agent — AI-Powered Business Intelligence & Sales Analytics Platform

An enterprise-grade **Business Intelligence (BI) and Decision-Support Platform** built with **Python, Streamlit, SQLite DBMS, Plotly, Monday.com API, and OpenAI** to analyze sales pipelines, revenue trends, customer segments, financial leakage, and operational performance.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://monday-bi-agent.streamlit.app/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repository-181717?logo=github)](https://github.com/HarshaVardhanReddyGujjula/Monday-BI-Agent)

🔗 **Live Interactive Demo:** [monday-bi-agent.streamlit.app](https://monday-bi-agent.streamlit.app/)  
📂 **Source Code:** [github.com/HarshaVardhanReddyGujjula/Monday-BI-Agent](https://github.com/HarshaVardhanReddyGujjula/Monday-BI-Agent)

---

## 🎯 Overview & Business Value

Monday BI Agent is designed from a **Senior Business Analyst perspective** to translate complex transactional records, remote API pipelines, and relational database tables into actionable executive insights.

It solves real-world corporate challenges:
- **Pipeline Visibility:** Tracking total vs. probability-weighted sales pipeline value and deal stage conversion velocity.
- **Financial Leakage Audits:** Identifying unbilled contracted work (**Billing Gap**) and unpaid client invoices (**Collection Gap**).
- **Executive Decision Support:** Interactive scenario analysis with dynamic multi-dimensional slicers and an embedded AI Business Analyst.
- **Data Democratization:** Live SQL Query Console and instant one-click executive report export to Microsoft Excel (`.xlsx`) and CSV.

---

## 🚀 Key Features

### 1. 📈 Executive KPI Scorecards
- **Total & Weighted Pipeline Value:** Computes probability-adjusted sales projections ($ \sum (\text{Deal Value} \times \text{Probability}) $).
- **Revenue Realization & Collected Cash:** Tracks contracted values against realized cash flows.
- **Collection Efficiency & Completion Gauges:** Visual health indicators with target thresholds ($ \ge 85\% $).

### 2. 🔍 Multi-Dimensional Dynamic Slicers & Filters
- **Interactive Date Range Slicer:** Filter all metrics and time-series trends by opportunity creation date.
- **Deal Stage / Status Filter:** Segment by *Closed Won, Negotiation, Proposal Sent, Qualified, Open, Dead*.
- **Sales Rep / Owner Filter:** Evaluate team and individual representative performance.
- **Client Tier Slicer:** Isolate metrics across *Enterprise, Mid-Market, and SMB* client portfolios.

### 3. 💼 Sales Performance & Historical Revenue Trends
- **Monthly Revenue & Deal Volume Trajectory:** Interactive dual-axis Plotly visualizations.
- **Sales Pipeline Funnel:** Stage-by-stage progression tracking and win-rate analysis.
- **High-Value Opportunity Tracker:** Automated sorting and prioritization of key strategic accounts.

### 4. 👥 Customer Insights & Product Category Analytics
- **Account Tier Segmentation:** Multi-dimensional revenue share analysis across enterprise, mid-market, and SMB clients.
- **Product Line Breakdown:** Identify top-performing business units (*Enterprise BI, Data Analytics, Cloud Integration, ERP Solutions*).

### 5. 💰 Financial Health & Cash-Flow Leakage Audit
- **Contract Value vs. Billed vs. Collected:** Granular cash-flow waterfall tracking.
- **Accounts Receivable Aging:** Automated overdue risk alerts and milestone billing status.
- **Operational Work Orders:** Track active, completed, and delayed client deliverables.

### 6. 🤖 AI Strategic Business Assistant
- **Dual-Mode Intelligence:** Connects to **OpenAI GPT-4o** when configured, or utilizes an **Advanced Built-in Deterministic Analytical Engine** when offline.
- **Actionable Business Queries:**
  - *"Which projects are delayed or at risk?"*
  - *"What is our collection gap and efficiency rate?"*
  - *"What is our billing gap and unbilled revenue?"*
  - *"Provide an executive business briefing and strategic recommendations."*

### 7. 🗄️ SQL Data Explorer & Excel Reporting
- **In-App SQL Console:** Run live analytical SQL queries directly over the relational SQLite database (`deals`, `work_orders`).
- **One-Click Export:** Download comprehensive executive reports in Excel format (`.xlsx`) with formatted worksheets for pipeline and operations.

---

## 🛠️ Architecture & Tech Stack

- **Data Processing & Analytics:** Python 3.10+, Pandas, NumPy
- **Relational DBMS & Querying:** SQLite3, SQL, SQLAlchemy
- **Dashboard & User Interface:** Streamlit, Modern CSS UI
- **Data Visualization:** Plotly Express, Plotly Graph Objects
- **APIs & Integration:** Monday.com GraphQL API (`requests`), OpenAI API (`gpt-4o`)
- **Reporting & Export:** XlsxWriter, OpenPyXL, CSV

```
Monday-BI-Agent/
│
├── dashboard.py         # Flagship Streamlit BI Dashboard with 6 analytical modules
├── bi_engine.py         # Core analytical engine, KPI calculations & DAX measures
├── data_processor.py    # Automated data cleaning, normalization & type inference
├── database.py          # SQLite relational database, schemas & sample enterprise seeder
├── ai_assistant.py      # Conversational AI Business Assistant (OpenAI + Offline Engine)
├── monday_client.py     # Production GraphQL client for Monday.com API
├── config.py            # Environment configurations and centralized logging
├── test_bi_agent.py     # End-to-end integration and pipeline test suite
├── requirements.txt     # Python package dependencies
├── .env.example         # Environment template
└── data/
    └── monday_bi.db     # Local SQLite relational database (auto-generated)
```

---

## ⚙️ Quick Start Installation

### 1. Clone the Repository
```bash
git clone https://github.com/HarshaVardhanReddyGujjula/Monday-BI-Agent.git
cd Monday-BI-Agent
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Dashboard (Zero-Configuration Demo Mode)
The application automatically provisions a local SQLite relational database with realistic enterprise datasets, allowing you to run it immediately without requiring external API keys:
```bash
streamlit run dashboard.py
```

### 4. (Optional) Configure Live Monday.com or OpenAI APIs
Create a `.env` file in the root directory:
```env
# Monday.com API (Optional - falls back to SQLite DBMS if omitted)
MONDAY_API_KEY=your_monday_api_token
MONDAY_BOARD_ID_DEALS=your_deals_board_id
MONDAY_BOARD_ID_WORK_ORDERS=your_work_orders_board_id

# OpenAI API (Optional - falls back to Offline Analytical Engine if omitted)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o
```

---

## 🧪 Testing

Execute the comprehensive integration test suite to verify database seeding, KPI computation, slicer filtering, and AI assistant reasoning:
```bash
python test_bi_agent.py
```

---

## 👨‍💻 Author

**Gujjula Harsha Vardhan Reddy**  
- **LinkedIn:** [linkedin.com/in/gujjula-harsha-vardhan-reddy-55a6403a7](https://www.linkedin.com/in/gujjula-harsha-vardhan-reddy-55a6403a7/)  
- **GitHub:** [github.com/HarshaVardhanReddyGujjula](https://github.com/HarshaVardhanReddyGujjula)
