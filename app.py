import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Ensure openpyxl is installed for Excel I/O
try:
    import openpyxl  # noqa: F401
except ImportError:
    st.error("The 'openpyxl' package is required to read/write Excel files. Please install it in your environment.")

# Constants
INVENTORY_FILE = "Inventory.xlsx"
EXPIRY_ALERT_DAYS = 30
DEFAULT_THRESHOLD = 1
DEFAULT_ORDER_QTY = 1

@st.cache_data(ttl=600)
def load_inventory():
    """
    Load inventory from Excel using openpyxl engine, with defaults and computed flags.
    """
    try:
        df = pd.read_excel(INVENTORY_FILE, engine='openpyxl')
    except FileNotFoundError:
        df = pd.DataFrame(columns=[
            "Item Category", "Item Name", "Expiration Date",
            "Manufacturer", "SKU", "Quantity in Stock",
            "Reorder Threshold", "Order Quantity"
        ])
    # Default columns
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
    Save inventory to Excel using openpyxl engine, dropping helper columns.
    """
    df_to_save = df.drop(columns=['Need Reorder'], errors='ignore')
    df_to_save.to_excel(INVENTORY_FILE, index=False, engine='openpyxl')

# Load data
df = load_inventory()

# Sidebar filters
st.sidebar.title("Filters")
categories = st.sidebar.multiselect(
    "Category", options=df['Item Category'].dropna().unique()
)
manufacturers = st.sidebar.multiselect(
    "Manufacturer", options=df['Manufacturer'].dropna().unique()
)
exp_range = st.sidebar.date_input(
    "Expiration Date Window",
    value=(datetime.today(), datetime.today() + timedelta(days=180))
)

# Apply filters
filtered = df.copy()
if categories:
    filtered = filtered[filtered['Item Category'].isin(categories)]
if manufacturers:
    filtered = filtered[filtered['Manufacturer'].isin(manufacturers)]
start_date, end_date = exp_range
filtered = filtered[filtered['Expiration Date']].between(
    pd.to_datetime(start_date), pd.to_datetime(end_date)
)
filtered = df[filtered]

# Tabs
tabs = st.tabs(["Overview", "Low Stock Alerts", "Receive Shipment"])

# Overview Tab
with tabs[0]:
    st.header("Overview")
    total_items = len(filtered)
    low_stock = int(filtered['Need Reorder'].sum())
    expiring_soon = int((filtered['Expiration Date'] <= datetime.today() + timedelta(days=EXPIRY_ALERT_DAYS)).sum())

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Items", total_items)
    c2.metric("Low Stock Items", low_stock)
    c3.metric(f"Expiring < {EXPIRY_ALERT_DAYS} days", expiring_soon)

    if expiring_soon > 0:
        st.warning(f"{expiring_soon} item(s) expiring within {EXPIRY_ALERT_DAYS} days.")

    st.dataframe(filtered)

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
    sku = st.text_input("Scan or Enter SKU:")
    qty = st.number_input("Quantity Received", min_value=1, value=1)
    date_received = st.date_input("Received Date", value=datetime.today())
    if st.button("Add to Inventory"):
        if not sku:
            st.error("SKU cannot be empty.")
        else:
            if sku in df['SKU'].astype(str).values:
                idx = df.index[df['SKU'].astype(str) == sku][0]
                df.at[idx, 'Quantity in Stock'] += qty
                st.success(f"Updated SKU {sku}: +{qty} units.")
            else:
                st.info(f"New SKU {sku} — please provide details below.")
                new_cat = st.text_input("Item Category")
                new_name = st.text_input("Item Name")
                new_exp = st.date_input("Expiration Date", value=date_received)
                new_man = st.text_input("Manufacturer")
                new_thresh = st.number_input("Reorder Threshold", min_value=1, value=DEFAULT_THRESHOLD)
                new_order_qty = st.number_input("Order Quantity", min_value=1, value=DEFAULT_ORDER_QTY)
                if st.button("Confirm Add New Item"):
                    new_row = pd.DataFrame([{
                        "Item Category": new_cat,
                        "Item Name": new_name,
                        "Expiration Date": new_exp,
                        "Manufacturer": new_man,
                        "SKU": sku,
                        "Quantity in Stock": qty,
                        "Reorder Threshold": new_thresh,
                        "Order Quantity": new_order_qty,
                        "Need Reorder": qty <= new_thresh
                    }])
                    df = pd.concat([df, new_row], ignore_index=True)
                    st.success(f"Added new SKU {sku} with {qty} units.")
            df['Need Reorder'] = df['Quantity in Stock'] <= df['Reorder Threshold']
            save_inventory(df)

st.caption("Lab Inventory Dashboard — Streamlit")
