import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from agent.data import load_data
from agent.metrics import (
    revenue_vs_budget, gross_margin_trend, opex_breakdown,
    ebitda_by_month, cash_runway
)
from agent.intent import classify_intent, parse_month_from_text, parse_last_n


st.set_page_config(page_title="CFO Copilot (FP&A)", layout="wide")

@st.cache  
def _load():
    return load_data("fixtures")

actuals, budget, cash = _load()

st.title("📊 CFO Copilot — FP&A Mini Agent")

query = st.text_input(
    "Ask a finance question:",
    placeholder="e.g. 'What was June 2025 revenue vs budget?', 'Show Gross Margin % trend for last 3 months'"
)

entity = st.selectbox("Entity (optional)", ["(All)"] + sorted(actuals["entity"].unique().tolist()))
entity = None if entity == "(All)" else entity


if st.button("Run") and query:
    intent = classify_intent(query)
    month = parse_month_from_text(query)
    last_n = parse_last_n(query, default=3)

    # Revenue vs Budget
    if intent == "revenue_vs_budget":
        if not month:
            st.warning("Please include a month, e.g., 'June 2025'.")
        else:
            res = revenue_vs_budget(actuals, budget, month, entity)
            st.subheader(f"Revenue vs Budget — {res['month']} ({res['entity']})")

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Actual",
                x=["Actual"],
                y=[res["actual_usd"]/1e6],
                marker_color="#1f77b4",
                text=[f"${res['actual_usd']/1e6:.2f}M"],
                textposition="outside"
            ))
            fig.add_trace(go.Bar(
                name="Budget",
                x=["Budget"],
                y=[res["budget_usd"]/1e6],
                marker_color="#ff7f0e",
                text=[f"${res['budget_usd']/1e6:.2f}M"],
                textposition="outside"
            ))
            fig.update_layout(
                barmode="group",
                title="Revenue vs Budget (Million USD)",
                template="plotly_white",
                title_x=0.5,
                yaxis_title="USD (M)"
            )
            st.plotly_chart(fig, use_container_width=True)

    # Gross Margin Trend
    elif intent == "gross_margin_trend":
        df = gross_margin_trend(actuals, last_n=last_n, entity=entity)
        st.subheader(f"Gross Margin % Trend (last {last_n} months) — {entity or 'All'}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["month"],
            y=df["gross_margin_pct"],
            mode="lines+markers+text",
            text=[f"{v:.1f}%" for v in df["gross_margin_pct"]],
            textposition="top center",
            line=dict(width=3, color="#2ca02c"),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title="Gross Margin % Trend",
            yaxis_title="Gross Margin (%)",
            template="plotly_white",
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df)

    # Opex Breakdown
    elif intent == "opex_breakdown":
        if not month:
            st.warning("Please include a month, e.g., 'June 2025'.")
        else:
            df, total = opex_breakdown(actuals, month, entity)
            st.subheader(f"Opex Breakdown — {month} ({entity or 'All'}) — Total: ${total/1e6:.2f}M")

            df["amount_usd"] = pd.to_numeric(df["amount_usd"], errors="coerce").fillna(0)
            df = df.sort_values("amount_usd", ascending=False).reset_index(drop=True)

            labels = df["account_category"].tolist()
            values = df["amount_usd"].tolist()

            fig = go.Figure(go.Pie(
                labels=labels,
                values=values,
                hole=0.3,
                textinfo="label+percent",
                hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
                marker=dict(colors=px.colors.qualitative.Set2)
            ))
            fig.update_layout(title="Opex by Category (USD)", title_x=0.5, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df[["account_category", "amount_usd", "pct"]])

    # EBITDA
    elif intent == "ebitda_trend":
        df = ebitda_by_month(actuals if entity is None else actuals[actuals["entity"] == entity])
        st.subheader(f"EBITDA Trend — {entity or 'All'}")

        fig = go.Figure(go.Scatter(
            x=df["month"],
            y=df["EBITDA"],
            mode="lines+markers+text",
            text=[f"${v/1e6:.2f}M" for v in df["EBITDA"]],
            textposition="top center",
            line=dict(width=3, color="#9467bd"),
            marker=dict(size=8)
        ))
        fig.update_layout(
            title="EBITDA (USD)",
            yaxis_title="EBITDA (USD)",
            template="plotly_white",
            title_x=0.5
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df)

    # Cash Runway
    elif intent == "cash_runway":
        res = cash_runway(cash, actuals, lookback=3, entity=entity)
        st.subheader(f"Cash Runway — as of {res['as_of']} ({entity or 'All'})")

        col1, col2, col3 = st.columns(3)
        col1.metric("Cash Balance", f"${res['cash_usd']/1e6:,.1f}M")
        col2.metric("Avg Burn (3mo)", f"${(res['avg_monthly_burn_usd'] or 0)/1e6:,.1f}M")
        col3.metric("Runway", f"{res['runway_months']:.1f} months"
                    if res["runway_months"] != float("inf") else "∞")

        if "month" in cash.columns and "cash_balance_usd" in cash.columns:
            fig = go.Figure(go.Scatter(
                x=cash["month"],
                y=cash["cash_balance_usd"],
                mode="lines+markers+text",
                text=[f"${v/1e6:.1f}M" for v in cash["cash_balance_usd"]],
                textposition="top center",
                line=dict(width=3, color="#17becf"),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title="Cash Balance Trend (USD)",
                template="plotly_white",
                title_x=0.5,
                yaxis_title="Cash Balance (USD)"
            )
            st.plotly_chart(fig, use_container_width=True)


    else:
        st.info("I couldn't classify the question. Try asking about: 'revenue vs budget', 'gross margin', 'opex breakdown', 'EBITDA', or 'cash runway'.")
