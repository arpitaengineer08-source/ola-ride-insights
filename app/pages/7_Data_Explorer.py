"""Searchable, filterable raw-data view with export."""
import streamlit as st

import ui

df, fdf, f = ui.setup("Data Explorer", "🔎", "Search any booking or customer, then export the slice")
ui.empty_guard(fdf)

q = st.text_input("Search Booking ID or Customer ID", placeholder="e.g. CID954071 or CNR7153255142").strip()
cols = st.columns(3)
loc = cols[0].multiselect("Pickup location", sorted(fdf["Pickup_Location"].unique()))
pay = cols[1].multiselect("Payment method", sorted(fdf["Payment_Method"].dropna().unique()))
val = cols[2].slider("Booking value (₹)", int(fdf["Booking_Value"].min()), int(fdf["Booking_Value"].max()),
                     (int(fdf["Booking_Value"].min()), int(fdf["Booking_Value"].max())))

v = fdf
if q:
    v = v[v["Booking_ID"].str.contains(q, case=False, regex=False) | v["Customer_ID"].str.contains(q, case=False, regex=False)]
if loc:
    v = v[v["Pickup_Location"].isin(loc)]
if pay:
    v = v[v["Payment_Method"].isin(pay)]
v = v[v["Booking_Value"].between(*val)]

st.write(f"**{len(v):,}** rides match")
show_cols = ["Booking_ID", "Booking_Timestamp", "Customer_ID", "Vehicle_Type", "Booking_Status", "Pickup_Location",
             "Drop_Location", "Ride_Distance", "Booking_Value", "Payment_Method", "Driver_Ratings", "Customer_Rating",
             "Cancel_Reason", "Incomplete_Rides_Reason"]
st.dataframe(v[show_cols].head(2000), hide_index=True, width="stretch",
             column_config={"Booking_Timestamp": st.column_config.DatetimeColumn("When", format="DD MMM, HH:mm"),
                            "Booking_Value": st.column_config.NumberColumn("Value", format="₹%d")})
if len(v) > 2000:
    st.caption("Showing first 2,000 rows - the download contains all matches.")
ui.download_df(v[show_cols], "ola_filtered_rides.csv", "⬇️ Download all matching rows")
