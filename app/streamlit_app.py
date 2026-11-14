"""Ola Ride Insights - entry page (Overall view).

Run from the project root:   streamlit run app/streamlit_app.py
"""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Overall Performance", "🚕",
                      "Ride volume, booking outcomes and demand patterns · Bengaluru · July 2024")
ui.empty_guard(fdf)

k, d = A.kpis(fdf), A.period_delta(fdf)

# ---- KPI strip --------------------------------------------------------------
c = st.columns(6)
ui.kpi(c[0], "Total bookings", f"{k['bookings']:,}", d.get("bookings"), "%")
ui.kpi(c[1], "Success rate", f"{k['success_rate']:.1f}%", d.get("success_rate"), " pp")
ui.kpi(c[2], "Realised revenue", ui.inr(k["revenue"]), d.get("revenue"), "%")
ui.kpi(c[3], "Avg fare", f"₹{k['avg_fare']:,.0f}", d.get("avg_fare"), "%")
ui.kpi(c[4], "Avg trip distance", f"{k['avg_distance']:.1f} km")
ui.kpi(c[5], "Value lost to failures", ui.inr(k["leaked"]))
st.write("")
c = st.columns(6)
ui.kpi(c[0], "Cancellation rate", f"{k['cancel_rate']:.1f}%")
ui.kpi(c[1], "Driver-not-found rate", f"{k['dnf_rate']:.1f}%")
ui.kpi(c[2], "Incomplete (of successful)", f"{k['incomplete_rate']:.1f}%")
ui.kpi(c[3], "Driver rating", f"{k['driver_rating']:.2f} ★")
ui.kpi(c[4], "Customer rating", f"{k['customer_rating']:.2f} ★")
ui.kpi(c[5], "Unique customers", f"{k['customers']:,}")
st.write("")

# ---- Insights + funnel ------------------------------------------------------
left, right = st.columns([1.15, 1])
with left:
    st.subheader("🧠 Auto-generated insights")
    st.caption("Recomputed live from whatever filters you pick.")
    ui.insight_cards(A.generate_insights(fdf))
with right:
    fn = A.funnel(fdf)
    fig = go.Figure(go.Funnel(y=fn["stage"], x=fn["rides"], textinfo="value+percent initial",
                              marker=dict(color=[C.PALETTE["info"], "#BC8CFF", C.PALETTE["accent"], C.PALETTE["good"]])))
    ui.show(ui.style(fig, 420, "Booking-to-trip funnel"))

st.divider()

# ---- Ride volume over time ---------------------------------------------------
st.subheader("📈 Ride volume over time")
grain = st.segmented_control("View", ["Daily", "Hourly", "Weekday (avg per day)"], default="Daily") or "Daily"

if grain == "Daily":
    sd = A.status_by_day(fdf)
    fig = px.bar(sd, x="Booking_Date", y="rides", color="Booking_Status", color_discrete_map=C.STATUS_COLORS,
                 category_orders={"Booking_Status": C.STATUS_ORDER})
    ds = A.daily_series(fdf)
    fig.add_trace(go.Scatter(x=ds["Booking_Date"], y=ds["bookings_ma7"], name="7-day moving avg",
                             mode="lines", line=dict(color="white", width=2.5, dash="dot")))
    fig.update_layout(barmode="stack", xaxis_title=None, yaxis_title="Bookings")
elif grain == "Hourly":
    h = fdf.groupby(["Booking_Hour", "Booking_Status"], observed=True).size().rename("rides").reset_index()
    fig = px.bar(h, x="Booking_Hour", y="rides", color="Booking_Status", color_discrete_map=C.STATUS_COLORS,
                 category_orders={"Booking_Status": C.STATUS_ORDER})
    fig.update_layout(barmode="stack", xaxis=dict(dtick=1, title="Hour of day"), yaxis_title="Bookings")
else:
    per_day = fdf.groupby(["Booking_Date", "Day_Name"], observed=True).size().rename("n").reset_index()
    wd = per_day.groupby("Day_Name", observed=True)["n"].agg(["mean", "count"]).reindex(C.DAY_ORDER).reset_index()
    fig = px.bar(wd, x="Day_Name", y="mean", text=wd["mean"].round(0), custom_data=["count"])
    fig.update_traces(marker_color=C.PALETTE["accent"],
                      hovertemplate="%{x}<br>%{y:.0f} bookings/day<br>%{customdata[0]} days in sample<extra></extra>")
    fig.update_layout(xaxis_title=None, yaxis_title="Avg bookings per day")
    st.caption("Normalised per calendar day: July 2024 has five Mondays, Tuesdays and Wednesdays, so raw totals "
               "overstate those days.")
ui.show(ui.style(fig, 400))

# ---- Status breakdown + heatmap --------------------------------------------
a, b = st.columns([1, 1.4])
with a:
    st.subheader("🥧 Booking status breakdown")
    s = fdf["Booking_Status"].value_counts().reindex(C.STATUS_ORDER).dropna().reset_index()
    s.columns = ["status", "rides"]
    fig = px.pie(s, names="status", values="rides", hole=0.58, color="status", color_discrete_map=C.STATUS_COLORS)
    fig.update_traces(textinfo="percent+value", sort=False)
    fig.add_annotation(text=f"<b>{len(fdf):,}</b><br>bookings", showarrow=False, font=dict(size=15))
    ui.show(ui.style(fig, 400))
with b:
    st.subheader("🔥 Demand heat-map")
    norm = st.toggle("Normalise per calendar day", value=True)
    hm = A.demand_heatmap(fdf, per_day=norm)
    fig = px.imshow(hm, aspect="auto", color_continuous_scale=["#0E1117", "#3a4400", C.PALETTE["accent"]],
                    labels=dict(x="Hour of day", y="", color="Bookings"))
    fig.update_xaxes(dtick=1)
    ui.show(ui.style(fig, 360))
    st.caption("Demand is remarkably flat across hours and weekdays - there is no classic rush-hour peak in this "
               "dataset, so driver allocation should be driven by cancellation hot-spots rather than time-of-day.")
