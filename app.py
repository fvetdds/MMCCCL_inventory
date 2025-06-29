import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Constants
INVENTORY_FILE = "Inventory.xlsx"
EXPIRY_ALERT_DAYS = 30
DEFAULT_THRESHOLD = 1
DEFAULT_ORDER_QTY = 1

@st.cache_data(ttl=600)
def load_inventory():
    try:
        df = pd.read_excel(INVENTORY_FILE)
    except FileNotFoundError:
        # create an empty dataframe if file not found
        df = pd.DataFrame(columns=["Item Category", "Item Name", "Expiration Date",
                                    "Manufacturer", "SKU", "Quantity in Stock",
                                    "Reorder Threshold", "Order Quantity"])
    # ensure default columns exist
    for col, default in [("Reorder Threshold", DEFAULT_THRESHOLD), ("Order Quantity", DEFAULT_ORDER_QTY)]:
        if col not in df.columns:
            df[col] = default
    # compute 'Need Reorder'
    df['Need Reorder'] = df['Quantity in Stock'] <= df['Reorder Threshold']
    # parse dates
    df['Expiration Date'] = pd.to_datetime(df['Expiration Date'])
    return df

@st.cache_data
def save_inventory(df: pd.DataFrame):
    # drop helper column and save
    df.drop(columns=['Need Reorder'], inplace=True)
    df.to_excel(INVENTORY_FILE, index=False)

# Load data
df = load_inventory()

# Sidebar filters
st.sidebar.title("Filters")
categories = st.sidebar.multiselect("Category", options=df['Item Category'].unique())
manufacturers = st.sidebar.multiselect("Manufacturer", options=df['Manufacturer'].unique())
exp_range = st.sidebar.date_input("Expiration window", value=(datetime.today(), datetime.today() + timedelta(days=180)))

# Apply filters
filtered = df.copy()
if categories:
    filtered = filtered[filtered['Item Category'].isin(categories)]
if manufacturers:
    filtered = filtered[filtered['Manufacturer'].isin(manufacturers)]
start_date, end_date = exp_range
filtered = filtered[(filtered['Expiration Date'] >= pd.to_datetime(start_date)) &
                    (filtered['Expiration Date'] <= pd.to_datetime(end_date))]

# Tabs
tabs = st.tabs(["Overview", "Low Stock Alerts", "Receive Shipment"])

# Overview Tab
with tabs[0]:
    st.header("Overview")
    total_items = len(filtered)
    low_stock = filtered['Need Reorder'].sum()
    expiring_soon = (filtered['Expiration Date'] <= pd.to_datetime(datetime.today() + timedelta(days=EXPIRY_ALERT_DAYS))).sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Items", total_items)
    col2.metric("Low Stock Items", low_stock)
    col3.metric(f"Expiring in < {EXPIRY_ALERT_DAYS} days", expiring_soon)

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
    sku = st.text_input("Scan or Enter SKU")
    qty = st.number_input("Quantity Received", min_value=1, value=1)
    date_received = st.date_input("Received Date", value=datetime.today())
    if st.button("Add to Inventory"):
        if not sku:
            st.error("Please enter a SKU.")
        else:
            if sku in df['SKU'].values:
                idx = df.index[df['SKU'] == sku][0]
                df.at[idx, 'Quantity in Stock'] += qty
                st.success(f"Updated SKU {sku}: +{qty} units.")
            else:
                st.info(f"New SKU {sku} - please fill details below.")
                new_cat = st.text_input("Item Category")
                new_name = st.text_input("Item Name")
                new_exp = st.date_input("Expiration Date", value=date_received)
                new_man = st.text_input("Manufacturer")
                new_thresh = st.number_input("Reorder Threshold", min_value=1, value=DEFAULT_THRESHOLD)
                new_order_qty = st.number_input("Order Quantity", min_value=1, value=DEFAULT_ORDER_QTY)
                if st.button("Confirm Add New Item"):
                    new_row = {
                        "Item Category": new_cat,
                        "Item Name": new_name,
                        "Expiration Date": new_exp,
                        "Manufacturer": new_man,
                        "SKU": sku,
                        "Quantity in Stock": qty,
                        "Reorder Threshold": new_thresh,
                        "Order Quantity": new_order_qty
                    }
                    df = df.append(new_row, ignore_index=True)
                    st.success(f"Added new SKU {sku} with {qty} units.")
            # Recompute and save
            df['Need Reorder'] = df['Quantity in Stock'] <= df['Reorder Threshold']
            save_inventory(df)

st.caption("Lab inventory dashboard powered by Streamlit")