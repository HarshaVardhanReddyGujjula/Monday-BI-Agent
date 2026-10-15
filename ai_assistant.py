import os
import re
from typing import Dict, Any, Optional
from config import logger, OPENAI_API_KEY


class BusinessAssistant:
    """
    Business Intelligence Conversational AI Assistant.
    Provides strategic business recommendations, cash-flow leakage audits,
    and operational insights using GPT-4o (if API key is present) or
    an advanced Built-in Analytical Reasoning Engine when offline.
    """

    def __init__(self, summary: Optional[Dict[str, Any]] = None):
        self.openai_key = OPENAI_API_KEY
        self.client = None
        if self.openai_key:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                logger.warning(f"Could not initialize OpenAI client: {e}")

        self.summary: Dict[str, Any] = summary or {}

    def set_summary(self, summary: Dict[str, Any]) -> None:
        """Updates the cached summary context."""
        self.summary = summary

    def ask(self, query: str) -> str:
        """Processes a natural language query and returns business insights."""
        query_clean = query.strip()
        if not query_clean:
            return "Please provide a question regarding your sales pipeline, finances, or operations."

        # If live OpenAI client is configured, call GPT
        if self.client and self.openai_key:
            try:
                return self._ask_openai(query_clean)
            except Exception as e:
                logger.warning(f"OpenAI API call failed ({e}). Falling back to analytical engine.")

        # Fallback to deterministic Business Analyst reasoning engine
        return self._ask_analytical_engine(query_clean)

    def _ask_openai(self, query: str) -> str:
        """Queries OpenAI GPT with the live BI metrics context."""
        system_prompt = (
            "You are a Senior Strategic Business Analyst and BI Consultant. "
            "Analyze the provided enterprise KPI data and answer the user's questions clearly, "
            "citing specific numbers, KPIs, leakage points, and actionable business recommendations.\n\n"
            f"LIVE DASHBOARD DATA:\n{self.summary}"
        )

        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.2,
            max_tokens=650
        )
        return response.choices[0].message.content

    def _ask_analytical_engine(self, query: str) -> str:
        """
        Rule-based analytical intelligence engine that provides structured,
        data-backed Business Analyst answers even without an external API key.
        """
        q = query.lower()

        deals = self.summary.get("Deals", {})
        wo = self.summary.get("Work_Orders", {})
        fin = self.summary.get("Financial", {})
        ops = self.summary.get("Operations", {})

        pipe_val = deals.get("total_pipeline_value", 0.0)
        weighted_val = deals.get("weighted_pipeline_value", 0.0)
        win_rate = deals.get("win_rate_pct", 0.0)
        total_deals = deals.get("total_deals", 0)

        rev = fin.get("revenue", 0.0)
        billed = fin.get("billed", 0.0)
        collected = fin.get("collected", 0.0)
        rec = fin.get("receivables", 0.0)
        billing_gap = fin.get("billing_gap", 0.0)
        collection_gap = fin.get("collection_gap", 0.0)
        coll_eff = wo.get("collection_efficiency", 0.0)

        delayed = ops.get("delayed_projects", 0)
        completed = ops.get("completed_projects", 0)
        total_proj = ops.get("total_projects", 0)
        comp_rate = ops.get("completion_rate", 0.0)

        # 1. Delayed / At Risk Projects
        if any(w in q for w in ["delayed", "delay", "risk", "stuck", "pause", "blocked"]):
            return (
                f"🚨 **Operational Risk Analysis: Delayed Projects**\n\n"
                f"- **Delayed / At-Risk Projects:** {delayed} out of {total_proj} total work orders.\n"
                f"- **Average Project Completion:** {comp_rate:.1f}%\n"
                f"- **Key Bottleneck Identified:** Work orders in 'Delayed / At Risk' or 'Pause' state "
                f"directly contribute to unbilled inventory and delayed receivables.\n\n"
                f"**Strategic BA Recommendation:**\n"
                f"1. Conduct a milestone sprint review with project leads on the {delayed} flagged work orders.\n"
                f"2. Validate client sign-offs for executed stages to unblock milestone billing."
            )

        # 2. Collection Efficiency / Gap / Receivables
        if any(w in q for w in ["collection", "receivable", "cash", "collected", "uncollected"]):
            return (
                f"💰 **Financial Health: Collection Efficiency & Accounts Receivable**\n\n"
                f"- **Total Billed Amount:** ₹{billed:,.2f}\n"
                f"- **Total Collected:** ₹{collected:,.2f}\n"
                f"- **Outstanding Receivables:** ₹{rec:,.2f}\n"
                f"- **Collection Efficiency Rate:** **{coll_eff:.1f}%** (Target: ≥ 85%)\n"
                f"- **Collection Gap:** ₹{collection_gap:,.2f} awaiting realization.\n\n"
                f"**Strategic BA Recommendation:**\n"
                f"1. Implement a 30-day aged debtor review for all invoices with 'Partial' or 'Overdue' status.\n"
                f"2. Institute upfront retainer terms (25–30%) on new contracts to protect working capital."
            )

        # 3. Billing Gap / Revenue Leakage
        if any(w in q for w in ["billing gap", "leakage", "unbilled", "billed"]):
            return (
                f"📊 **Billing Realization & Revenue Leakage Audit**\n\n"
                f"- **Total Contracted Revenue:** ₹{rev:,.2f}\n"
                f"- **Total Invoiced / Billed:** ₹{billed:,.2f}\n"
                f"- **Billing Gap (Unbilled Revenue):** **₹{billing_gap:,.2f}**\n\n"
                f"**Root-Cause Insights:**\n"
                f"A billing gap of ₹{billing_gap:,.2f} indicates that executed work has not yet been converted "
                f"into commercial invoices. Expediting phase-completion sign-offs will immediately capture this unbilled value."
            )

        # 4. Pipeline / Deals / Sales Performance
        if any(w in q for w in ["pipeline", "deals", "sales", "win rate", "conversion"]):
            return (
                f"💼 **Sales Pipeline & Conversion Intelligence**\n\n"
                f"- **Total Pipeline Value:** ₹{pipe_val:,.2f} across {total_deals} opportunities.\n"
                f"- **Probability-Weighted Pipeline:** **₹{weighted_val:,.2f}**\n"
                f"- **Win Rate:** **{win_rate:.1f}%**\n"
                f"- **High-Probability Deals:** {deals.get('high_probability_deals', 0)} deals with ≥70% confidence.\n\n"
                f"**Strategic BA Recommendation:**\n"
                f"Focus sales management bandwidth on closing the {deals.get('high_probability_deals', 0)} high-probability "
                f"proposals in 'Negotiation' to guarantee revenue realization for the upcoming quarter."
            )

        # 5. Executive Summary / General Overview / Recommendations
        return (
            f"📈 **Executive Business Intelligence Briefing**\n\n"
            f"**1. Sales Health:** Pipeline stands at **₹{pipe_val:,.2f}** ({total_deals} deals) with a weighted realization of **₹{weighted_val:,.2f}** and a **{win_rate:.1f}%** win rate.\n"
            f"**2. Operations:** **{completed}/{total_proj}** projects delivered ({comp_rate:.1f}% completion rate) with **{delayed}** project(s) requiring active intervention.\n"
            f"**3. Cash Realization:** **₹{collected:,.2f}** collected against **₹{billed:,.2f}** billed (**{coll_eff:.1f}%** collection efficiency). Outstanding receivables: **₹{rec:,.2f}**.\n\n"
            f"**Top Strategic Priority:** Close the **₹{billing_gap:,.2f}** billing gap by accelerating milestone completions and formalizing invoice schedules."
        )
