"""View 5 - Ratings."""
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Ratings", "⭐", "Driver and customer satisfaction on completed trips")
s = fdf[fdf["Is_Success"] == 1]
if s.empty:
    st.warning("Ratings exist only for successful rides - none match the current filters.")
    st.stop()

low_d = 100 * (s["Driver_Ratings"] < 3.5).mean()
low_c = 100 * (s["Customer_Rating"] < 3.5).mean()
c = st.columns(5)
ui.kpi(c[0], "Avg driver rating", f"{s['Driver_Ratings'].mean():.2f} ★")
ui.kpi(c[1], "Avg customer rating", f"{s['Customer_Rating'].mean():.2f} ★")
ui.kpi(c[2], "Driver ratings < 3.5", f"{low_d:.1f}%")
ui.kpi(c[3], "Customer ratings < 3.5", f"{low_c:.1f}%")
ui.kpi(c[4], "Rating correlation (D vs C)", f"{s['Driver_Ratings'].corr(s['Customer_Rating']):+.3f}")
st.write("")

a, b = st.columns(2)
for col, field, title, color in [(a, "Driver_Ratings", "Driver ratings distribution", C.PALETTE["info"]),
                                 (b, "Customer_Rating", "Customer ratings distribution", C.PALETTE["accent"])]:
    with col:
        vc = s[field].round(1).value_counts().sort_index().reset_index()
        vc.columns = ["rating", "rides"]
        fig = px.bar(vc, x="rating", y="rides")
        fig.update_traces(marker_color=color)
        fig.add_vline(x=s[field].mean(), line_dash="dot", annotation_text=f"mean {s[field].mean():.2f}")
        fig.update_layout(xaxis_title="Rating", yaxis_title="Rides")
        ui.show(ui.style(fig, 340, title))
st.caption("Ratings are spread almost uniformly between 3.0 and 5.0 (with half-weight at the 3.0 / 5.0 edges) and "
           "nobody rates below 3 - a sign of rating inflation or of a floor in the app.")

a, b = st.columns(2)
with a:
    rv = s.groupby("Vehicle_Type", observed=True)[["Driver_Ratings", "Customer_Rating"]].mean().reset_index()
    m = rv.melt("Vehicle_Type", var_name="who", value_name="rating")
    m["who"] = m["who"].map({"Driver_Ratings": "Driver", "Customer_Rating": "Customer"})
    fig = px.bar(m, x="Vehicle_Type", y="rating", color="who", barmode="group", text=m["rating"].round(3),
                 color_discrete_map={"Driver": C.PALETTE["info"], "Customer": C.PALETTE["accent"]},
                 category_orders={"Vehicle_Type": C.VEHICLE_ORDER})
    fig.update_yaxes(range=[3.9, 4.1])
    fig.update_layout(xaxis_title=None, yaxis_title="Average rating", legend_title=None)
    ui.show(ui.style(fig, 380, "Average rating by vehicle type"))
    st.caption("⚠️ y-axis zoomed to 3.9-4.1: differences between vehicles are tiny (< 0.03 ★).")
with b:
    H, xe, ye = np.histogram2d(s["Customer_Rating"], s["Driver_Ratings"], bins=[np.arange(2.95, 5.15, 0.1)] * 2)
    fig = go.Figure(go.Heatmap(z=H.T, x=np.round(xe[:-1] + 0.05, 1), y=np.round(ye[:-1] + 0.05, 1),
                               colorscale=["#0E1117", "#3a4400", C.PALETTE["accent"]]))
    fig.update_layout(xaxis_title="Customer rating", yaxis_title="Driver rating")
    ui.show(ui.style(fig, 380, "Customer vs driver rating (ride density)"))
    st.caption("A uniform square means the two ratings are independent - a happy customer does not predict a "
               "highly-rated driver.")

a, b = st.columns(2)
with a:
    pm = s.groupby("Payment_Method")[["Driver_Ratings", "Customer_Rating"]].mean().round(3)
    st.markdown("**Average rating by payment method**")
    st.dataframe(pm, width="stretch")
with b:
    tb = s.groupby("Time_Band", observed=True)[["Driver_Ratings", "Customer_Rating"]].mean().round(3)
    st.markdown("**Average rating by time of day**")
    st.dataframe(tb, width="stretch")
