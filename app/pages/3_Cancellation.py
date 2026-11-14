"""View 4 - Cancellation."""
import plotly.express as px
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Cancellation", "🚫", "Why rides fail, who cancels, and where the money leaks")
ui.empty_guard(fdf)

k = A.kpis(fdf)
cc = fdf["Booking_Status"].eq("Canceled by Customer").sum()
dc = fdf["Booking_Status"].eq("Canceled by Driver").sum()
dnf = fdf["Booking_Status"].eq("Driver Not Found").sum()
c = st.columns(5)
ui.kpi(c[0], "Cancelled by customer", f"{cc:,}")
ui.kpi(c[1], "Cancelled by driver", f"{dc:,}")
ui.kpi(c[2], "Driver not found", f"{dnf:,}")
ui.kpi(c[3], "Overall failure rate", f"{100 - k['success_rate']:.1f}%")
ui.kpi(c[4], "Booking value leaked", ui.inr(k["leaked"]))
st.write("")


def reasons(party: str, title: str, color: str):
    r = fdf[fdf["Cancel_Party"] == party]["Cancel_Reason"].value_counts().reset_index()
    r.columns = ["reason", "rides"]
    r["pct"] = 100 * r["rides"] / r["rides"].sum() if len(r) else 0
    r = r.sort_values("rides")
    fig = px.bar(r, x="rides", y="reason", orientation="h", text=r.apply(lambda x: f"{x.rides:,} · {x.pct:.1f}%", axis=1))
    fig.update_traces(marker_color=color, textposition="outside", cliponaxis=False)
    fig.update_layout(yaxis_title=None, xaxis_title="Cancellations", xaxis_range=[0, r["rides"].max() * 1.35] if len(r) else None)
    return ui.style(fig, 340, title)


a, b = st.columns(2)
with a:
    ui.show(reasons("Customer", "Why customers cancel", C.STATUS_COLORS["Canceled by Customer"]))
with b:
    ui.show(reasons("Driver", "Why drivers cancel", C.STATUS_COLORS["Canceled by Driver"]))

a, b = st.columns(2)
with a:
    hr = fdf.groupby("Booking_Hour")["Is_Success"].agg(lambda s: 100 * (1 - s.mean())).reset_index(name="fail")
    fig = px.line(hr, x="Booking_Hour", y="fail", markers=True)
    fig.update_traces(line_color=C.PALETTE["bad"])
    fig.add_hline(y=100 - k["success_rate"], line_dash="dot", annotation_text="average")
    fig.update_layout(xaxis=dict(dtick=2, title="Hour of day"), yaxis_title="Failure rate (%)")
    ui.show(ui.style(fig, 360, "Failure rate by hour"))
with b:
    leak = (fdf[fdf["Is_Success"] == 0].groupby(["Vehicle_Type", "Booking_Status"], observed=True)["Booking_Value"]
            .sum().reset_index())
    fig = px.bar(leak, x="Vehicle_Type", y="Booking_Value", color="Booking_Status",
                 color_discrete_map=C.STATUS_COLORS, category_orders={"Vehicle_Type": C.VEHICLE_ORDER})
    fig.update_layout(barmode="stack", xaxis_title=None, yaxis_title="Value lost (₹)")
    ui.show(ui.style(fig, 360, "Revenue leakage by vehicle and cause"))

st.subheader("📍 Pickup hot-spots")
min_n = st.slider("Minimum bookings per location", 100, 2000, min(1000, max(100, len(fdf) // 60)), step=50)
loc = fdf.groupby("Pickup_Location").agg(bookings=("Booking_ID", "count"), fail=("Is_Success", lambda s: 100 * (1 - s.mean())))
loc = loc[loc["bookings"] >= min_n].sort_values("fail", ascending=False)
if loc.empty:
    st.info("No location meets the minimum bookings threshold.")
else:
    top = loc.head(10).reset_index().iloc[::-1]
    fig = px.bar(top, x="fail", y="Pickup_Location", orientation="h", text=top["fail"].round(1), color="fail",
                 color_continuous_scale=["#3a4400", C.PALETTE["bad"]])
    fig.update_layout(coloraxis_showscale=False, xaxis_title="Failure rate (%)", yaxis_title=None)
    fig.update_xaxes(range=[loc["fail"].min() - 3, loc["fail"].max() + 1])
    ui.show(ui.style(fig, 400, "Top 10 pickup zones by failure rate"))
    st.caption(f"Spread between best and worst zone is only {loc['fail'].max() - loc['fail'].min():.1f} pp "
               "- the issue is systemic, not a few bad neighbourhoods. (x-axis zoomed to show the gap.)")

with st.expander("🔁 Serial cancellers (customers with 2+ cancellations)"):
    sc = (fdf[fdf["Booking_Status"] == "Canceled by Customer"].groupby("Customer_ID")
          .agg(cancellations=("Booking_ID", "count"), blocked_value=("Booking_Value", "sum"))
          .query("cancellations >= 2").sort_values(["cancellations", "blocked_value"], ascending=False))
    st.write(f"{len(sc):,} customers - candidates for a cancellation-fee nudge.")
    st.dataframe(sc.head(50), width="stretch")
