import os
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="centered", page_title="Retail Sales Dashboard")

@st.cache_data
def load_data(path="data/clean_retail.csv"):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Run from project root or adjust path.")
    # try to parse dates, be defensive
    df = pd.read_csv(path, encoding="utf-8", low_memory=False)
    # ensure common column names no trailing spaces
    df.columns = df.columns.str.strip()
    # convert InvoiceDate to datetime (coerce bad values to NaT)
    if "InvoiceDate" in df.columns:
        df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    # Ensure numeric columns
    if "TotalPrice" in df.columns:
        df["TotalPrice"] = pd.to_numeric(df["TotalPrice"], errors="coerce").fillna(0)
    if "Quantity" in df.columns:
        df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    # If Cluster missing, create a default cluster column
    if "Cluster" not in df.columns:
        df["Cluster"] = "Unknown"
    # Fill missing cluster (optional)
    df["Cluster"] = df["Cluster"].fillna("Unknown")
    return df

# Load and show diagnostics
try:
    with st.spinner("Loading data..."):
        df = load_data()
except Exception as e:
    st.error(f"Failed to load data: {e}")
    st.stop()

st.title("Retail Sales Dashboard – Customer & Segmentation Insights")
st.markdown("Use this dashboard to explore retail sales & clustering results.")

# Diagnostics area so you can see what's loaded
st.sidebar.header("Diagnostics")
st.sidebar.write("Rows, Columns:")
st.sidebar.write(df.shape)
st.sidebar.write("Columns:")
st.sidebar.write(list(df.columns))
st.sidebar.write("Preview:")
st.sidebar.dataframe(df.head(5))

# Sidebar filters (guard against weird dtypes)
try:
    cluster_options = df['Cluster'].astype(str).unique().tolist()
except Exception:
    cluster_options = ["Unknown"]
selected_cluster = st.sidebar.multiselect("Select cluster(s)", cluster_options, default=cluster_options)

# Filtered data
filtered = df[df['Cluster'].astype(str).isin(selected_cluster)].copy()
st.write(f"Filtered rows: {filtered.shape[0]}")

# Top products by revenue
st.subheader("Top Products by Revenue")
if "Description" not in filtered.columns or "TotalPrice" not in filtered.columns:
    st.warning("Missing `Description` or `TotalPrice` in data. Check CSV columns.")
else:
    product_summary = (
        filtered.groupby('Description', dropna=False)
                .agg(Total_Revenue=('TotalPrice', 'sum'),
                     Total_Quantity=('Quantity', 'sum'))
                .reset_index()
                .sort_values(by='Total_Revenue', ascending=False)
                .head(10)
    )
    st.dataframe(product_summary)
    if not product_summary.empty:
        fig_prod = px.bar(product_summary, x='Total_Revenue', y='Description', orientation='h',
                          title="Top 10 Products by Revenue", labels={'Total_Revenue': 'Revenue'})
        st.plotly_chart(fig_prod)
    else:
        st.info("No top products to show for current filters.")

# Monthly trend view
st.subheader("Monthly Revenue Trend")
if "InvoiceDate" not in filtered.columns:
    st.warning("Missing `InvoiceDate` column. Cannot build monthly trend.")
else:
    monthly = (
        filtered.assign(YearMonth=filtered['InvoiceDate'].dt.to_period('M'))
                .groupby('YearMonth')['TotalPrice']
                .sum()
                .reset_index()
    )
    if monthly.empty:
        st.info("No monthly revenue data (InvoiceDate may be all NaT).")
    else:
        monthly['YearMonth'] = monthly['YearMonth'].astype(str)
        fig_month = px.line(monthly, x='YearMonth', y='TotalPrice', title='Monthly Revenue')
        st.plotly_chart(fig_month)

# Customer segments overview
st.subheader("Customer Segments Overview")
if "CustomerID" not in filtered.columns:
    st.warning("Missing `CustomerID`. Segment counts use CustomerID to count unique customers.")
else:
    segments = (
        filtered.groupby('Cluster')
                .agg(Count=('CustomerID', 'nunique'),
                     Avg_Monetary=('TotalPrice', 'mean'),
                     Avg_Frequency=('Quantity', 'sum'))
                .reset_index()
    )
    st.dataframe(segments)
    if not segments.empty:
        fig_seg = px.bar(segments, x='Cluster', y='Count', title='Customer Segment Sizes')
        st.plotly_chart(fig_seg)

st.markdown("### Insights & Next Steps")
st.markdown("""
- Use the filters above to focus on specific customer clusters.
- If anything is missing, check the CSV headers and data types (see 'Diagnostics' in the sidebar).
- Check the terminal logs for full tracebacks if `Failed to load data` appears.
""")
