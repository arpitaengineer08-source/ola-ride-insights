"""View 2 - Vehicle type (mirrors slide 2 and slide 5 of the Power BI brief)."""
import pandas as pd
import plotly.express as px
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Vehicle Type", "🚗", "Which vehicle types move the most people, distance and money")
ui.empty_guard(fdf)

vs = A.vehicle_summary(fdf)
icons = ui.get_vehicle_dim()[["Vehicle_Type", "Icon_URL"]]
vs = vs.merge(icons, on="Vehicle_Type", how="left")

st.subheader("📋 Vehicle scorecard")
st.dataframe(
    vs[["Icon_URL", "Vehicle_Type", "total_booking_value", "success_booking_value", "avg_distance_km",
        "total_distance_km", "success_rate", "driver_rating", "customer_rating"]],
    hide_index=True, width="stretch",
    column_config={
        "Icon_URL": st.column_config.ImageColumn("", width="small"),
        "Vehicle_Type": "Vehicle Type",
        "total_booking_value": st.column_config.NumberColumn("Total Booking Value", format="₹%d"),
        "success_booking_value": st.column_config.ProgressColumn(
            "Success Booking Value", format="₹%d", min_value=0, max_value=max(float(vs["success_booking_value"].max()), 1.0)),
        "avg_distance_km": st.column_config.NumberColumn("Avg. Distance (km)", format="%.1f"),
        "total_distance_km": st.column_config.NumberColumn("Total Distance (km)", format="%d"),
        "success_rate": st.column_config.NumberColumn("Success %", format="%.1f%%"),
        "driver_rating": st.column_config.NumberColumn("Driver ★", format="%.2f"),
        "customer_rating": st.column_config.NumberColumn("Customer ★", format="%.2f"),
    })

a, b = st.columns(2)
with a:
    metric = st.radio("Rank by", ["Total distance (km)", "Average distance (km)"], horizontal=True)
    col = "total_distance_km" if metric.startswith("Total") else "avg_distance_km"
    top5 = vs.nlargest(5, col).sort_values(col)
    fig = px.bar(top5, x=col, y="Vehicle_Type", orientation="h", color="Vehicle_Type",
                 color_discrete_map=C.VEHICLE_COLORS, text=top5[col].round(1 if col.startswith("avg") else 0))
    fig.update_layout(showlegend=False, yaxis_title=None, xaxis_title=metric)
    ui.show(ui.style(fig, 360, "Top 5 vehicle types by ride distance"))
with b:
    fig = px.scatter(vs, x="avg_distance_km", y="avg_fare", size="bookings", color="Vehicle_Type",
                     color_discrete_map=C.VEHICLE_COLORS, size_max=45, hover_data={"success_rate": ":.1f"})
    fig.update_layout(xaxis_title="Avg distance (km)", yaxis_title="Avg fare (₹)")
    ui.show(ui.style(fig, 360 + 36, "Distance vs fare - the Auto outlier"))

a, b = st.columns(2)
with a:
    mix = (fdf.groupby(["Vehicle_Type", "Booking_Status"], observed=True).size()
              .groupby(level=0, observed=True).transform(lambda s: 100 * s / s.sum()).rename("pct").reset_index())
    fig = px.bar(mix, x="pct", y="Vehicle_Type", color="Booking_Status", orientation="h",
                 color_discrete_map=C.STATUS_COLORS, category_orders={"Booking_Status": C.STATUS_ORDER,
                                                                      "Vehicle_Type": C.VEHICLE_ORDER[::-1]})
    fig.update_layout(barmode="stack", xaxis_title="% of bookings", yaxis_title=None)
    ui.show(ui.style(fig, 380, "Outcome mix per vehicle"))
with b:
    fig = px.bar(vs.sort_values("success_booking_value"), x="success_booking_value", y="Vehicle_Type",
                 orientation="h", color="Vehicle_Type", color_discrete_map=C.VEHICLE_COLORS,
                 text=vs.sort_values("success_booking_value")["success_booking_value"].map(ui.inr))
    fig.update_layout(showlegend=False, xaxis_title="Realised revenue (₹)", yaxis_title=None)
    ui.show(ui.style(fig, 380, "Realised revenue by vehicle"))

st.subheader("⭐ Ratings at a glance")
cols = st.columns(4)
for i, r in enumerate(vs.itertuples()):
    with cols[i % 4]:
        with st.container(border=True):
            st.image(r.Icon_URL, width=44)
            st.markdown(f"**{r.Vehicle_Type}**")
            if pd.isna(r.driver_rating):
                st.caption("No successful rides in the current filters")
            else:
                st.caption(f"Driver ★ {r.driver_rating:.2f} · Customer ★ {r.customer_rating:.2f}")
                st.caption(f"Success rate {r.success_rate:.1f}% · Avg fare ₹{r.avg_fare:,.0f}")
