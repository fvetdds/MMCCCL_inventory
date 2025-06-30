import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# File definitions
EXCEL_FILE = "/mnt/data/Inventory.xlsx"  # updated path to uploaded file
CSV_FILE = "Inventory.csv"
EXPIRY_ALERT_DAYS = 30
DEFAULT_THRESHOLD = 1
DEFAULT_ORDER_QTY = 1

@st.cache_data(ttl=600)
def load_inventory():
    """
    Load inventory from Excel; fall back to CSV if needed.
    """
    try:
        df = pd.read_excel(EXCEL_FILE, engine='openpyxl')
    except Exception:
        try:
            df = pd.read_csv(CSV_FILE)
        except FileNotFoundError:
            df = pd.DataFrame(columns=[
                "Item Category", "Item Name", "Expiration Date",
                "Manufacturer", "SKU", "Quantity in Stock",
                "Reorder Threshold", "Order Quantity"
            ])
    # Ensure required columns exist
    if 'Quantity in Stock' not in df.columns:
        df['Quantity in Stock'] = 0
    for col, default in [("Reorder Threshold", DEFAULT_THRESHOLD), ("Order Quantity", DEFAULT_ORDER_QTY)]:
        if col not in df.columns:
            df[col] = default
    # Compute reorder flag
    df['Need Reorder'] = df['Quantity in Stock'] <= df['Reorder Threshold']
    # Parse dates
    if 'Expiration Date' in df.columns:
        df['Expiration Date'] = pd.to_datetime(df['Expiration Date'], errors='coerce')
    else:
        df['Expiration Date'] = pd.NaT
    return df

@st.cache_data
def save_inventory(df: pd.DataFrame):
    """
    Save inventory to Excel or CSV.
    """
    df_to_save = df.drop(columns=['Need Reorder'], errors='ignore')
    try:
        df_to_save.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
    except Exception:
        df_to_save.to_csv(CSV_FILE, index=False)

# Load data
df = load_inventory()

# No expiration filter applied
filtered = df.copy()

# Tabs for display
tabs = st.tabs(["Overview", "Low Stock Alerts", "Receive Shipment"])

# Overview Tab
with tabs[0]:
    st.header("Overview")
    # Show Item Name and Quantity for all inventory items
    overview_df = df[["Item Name", "Quantity in Stock"]]
    st.subheader("Current Stock Levels")
    st.dataframe(overview_df)

# Low Stock Alerts Tab
with tabs[1]:
    st.header("Items Needing Reorder")
    alerts = filtered[filtered['Need Reorder']]
    if alerts.empty:
        st.success("No items need reordering.")
    else:
        st.dataframe(alerts)

# Receive Shipment Tab
with tabs[2]:
    st.header("Receive Shipment")
    # Select existing item names
    item = st.selectbox("Select Item", options=df['Item Name'].dropna().unique())
    qty = st.number_input("Quantity Received", min_value=1, value=1)
    date_received = st.date_input("Received Date", value=datetime.today())

    if st.button("Add to Inventory"):
        if not item:
            st.error("Please select an item.")
        else:
            idx_list = df.index[df['Item Name'] == item].tolist()
            if idx_list:
                idx = idx_list[0]
                df.at[idx, 'Quantity in Stock'] += qty
                st.success(f"Updated '{item}': +{qty} units.")
            else:
                st.error(f"Item '{item}' not found in inventory.")
        # Recompute and save
        df['Need Reorder'] = df['Quantity in Stock'] <= df['Reorder Threshold']
        save_inventory(df)

st.caption("Lab Inventory Dashboard — Streamlit")
