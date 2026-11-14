"""View 3 - Revenue."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Revenue", "💰", "Payment mix, top customers and distance patterns")
ui.empty_guard(fdf)

basis = st.radio("Value basis", ["Realised revenue (successful rides)", "Gross booking value (all bookings)"],
                 horizontal=True)
succ_only = basis.startswith("Realised")
base = fdf[fdf["Is_Success"] == 1] if succ_only else fdf
if base.empty:
    st.warning("No rides under this basis for the current filters.")
    st.stop()

s = fdf[fdf["Is_Success"] == 1]
c = st.columns(4)
ui.kpi(c[0], "Total value", ui.inr(base["Booking_Value"].sum()))
ui.kpi(c[1], "Average value / booking", f"₹{base['Booking_Value'].mean():,.0f}")
ui.kpi(c[2], "Revenue per km (successful)", f"₹{s['Booking_Value'].sum() / max(s['Ride_Distance'].sum(), 1):.1f}")
ui.kpi(c[3], "Digital payment share", f"{100 * s['Payment_Method'].isin(['UPI', 'Credit Card', 'Debit Card']).mean():.1f}%")
st.write("")

a, b = st.columns(2)
with a:
    pay = s.groupby("Payment_Method").agg(revenue=("Booking_Value", "sum"), rides=("Booking_ID", "count")).reset_index()
    fig = px.bar(pay.sort_values("revenue", ascending=False), x="Payment_Method", y="revenue", color="Payment_Method",
                 text=pay.sort_values("revenue", ascending=False)["revenue"].map(ui.inr), custom_data=["rides"])
    fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Revenue (₹)")
    fig.update_traces(hovertemplate="%{x}<br>%{y:,.0f} ₹<br>%{customdata[0]:,} rides<extra></extra>")
    ui.show(ui.style(fig, 380, "Revenue by payment method"))
    st.caption("Payment method exists only for successful rides, so this chart is always on realised revenue.")
with b:
    cust = (base.groupby("Customer_ID").agg(value=("Booking_Value", "sum"), rides=("Booking_ID", "count"))
                .sort_values(["value", "rides"], ascending=False).head(5).reset_index().iloc[::-1])
    fig = px.bar(cust, x="value", y="Customer_ID", orientation="h", text=cust["value"].map(ui.inr),
                 custom_data=["rides"])
    fig.update_traces(marker_color=C.PALETTE["accent"],
                      hovertemplate="%{y}<br>₹%{x:,.0f} over %{customdata[0]} rides<extra></extra>")
    fig.update_layout(xaxis_title="Total booking value (₹)", yaxis_title=None)
    ui.show(ui.style(fig, 380, "Top 5 customers by total booking value"))

st.subheader("📏 Ride distance distribution per day")
mode = st.radio("Show", ["Box per day", "Total km per day"], horizontal=True)
if mode == "Box per day":
    fig = px.box(s, x="Booking_Date", y="Ride_Distance", points=False)
    fig.update_traces(marker_color=C.PALETTE["accent"], line_color=C.PALETTE["accent"])
    fig.update_layout(xaxis_title=None, yaxis_title="Ride distance (km)")
else:
    dd = s.groupby("Booking_Date")["Ride_Distance"].sum().reset_index()
    fig = px.bar(dd, x="Booking_Date", y="Ride_Distance")
    fig.update_traces(marker_color=C.PALETTE["accent"])
    fig.update_layout(xaxis_title=None, yaxis_title="Total km")
ui.show(ui.style(fig, 380))

a, b = st.columns(2)
with a:
    ds = A.daily_series(fdf)
    ds["cumulative"] = ds["revenue"].cumsum()
    fig = go.Figure()
    fig.add_bar(x=ds["Booking_Date"], y=ds["revenue"], name="Daily revenue", marker_color="#3a4400")
    fig.add_scatter(x=ds["Booking_Date"], y=ds["cumulative"], name="Cumulative", yaxis="y2",
                    line=dict(color=C.PALETTE["accent"], width=3))
    fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False), yaxis_title="Daily (₹)",
                      legend=dict(orientation="h", y=1.12))
    ui.show(ui.style(fig, 380, "Daily and cumulative realised revenue"))
with b:
    hist = px.histogram(s, x="Ride_Distance", color="Vehicle_Type", nbins=25, barmode="overlay", opacity=0.6,
                        color_discrete_map=C.VEHICLE_COLORS, category_orders={"Vehicle_Type": C.VEHICLE_ORDER})
    hist.update_layout(xaxis_title="Ride distance (km)", yaxis_title="Rides")
    ui.show(ui.style(hist, 380, "Distance distribution by vehicle (Auto is capped at 19 km)"))
