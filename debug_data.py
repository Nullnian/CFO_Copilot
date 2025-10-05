import streamlit as st
import pandas as pd
from agent.data import load_data

st.set_page_config(layout="wide")

st.header("Data Debug")

actuals, budget, cash = load_data("fixtures")

st.subheader("actuals (head)")
st.dataframe(actuals.head(10))
st.write("Rows:", len(actuals))

st.subheader("budget (head)")
st.dataframe(budget.head(10))
st.write("Rows:", len(budget))

st.subheader("cash (head)")
st.dataframe(cash.head(10))
st.write("Rows:", len(cash))
