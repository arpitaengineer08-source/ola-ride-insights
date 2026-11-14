"""Business storytelling: findings, recommendations and a what-if impact simulator."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, _, _ = ui.setup("Executive Brief", "🧭", "What the data says, what to do about it, and what it is worth", filters=False)
k = A.kpis(df)
s = df[df["Is_Success"] == 1]
n = len(df)
cc = df["Booking_Status"].eq("Canceled by Customer").sum()
dc = df["Booking_Status"].eq("Canceled by Driver").sum()
dnf = df["Booking_Status"].eq("Driver Not Found").sum()
seg = A.customer_segments(df).set_index("segment")["pct_customers"]
pay = s["Payment_Method"].value_counts(normalize=True) * 100
fare_avg = s["Booking_Value"].mean()

st.markdown(f"""
### The one-paragraph story
Ola Bengaluru took **{n:,} bookings in July 2024**, but only **{k['success_rate']:.1f}%** turned into rides.
The remaining **{ui.inr(k['leaked'])}** of booking value evaporated through driver cancellations ({dc:,}),
customer cancellations ({cc:,}) and unmatched requests ({dnf:,}). Demand itself is healthy and evenly spread
across hours and days - **the business problem is conversion, not demand**.
""")

st.subheader("Findings → actions")
rows = [
    ("🔴", "Driver cancellations are the biggest leak",
     f"{dc:,} rides ({100 * dc / n:.1f}% of bookings), led by *Personal & car related issue*.",
     "Pre-trip vehicle/availability check-in, cancellation penalties, and incentives for completion streaks."),
    ("🟠", "Customers cancel when the driver does not approach",
     "‘Driver is not moving towards pickup’ and ‘Driver asked to cancel’ together are over half of customer cancels.",
     "Live ETA drift alerts, auto-reassign after 90 s of no movement, ban driver-initiated cancel requests."),
    ("🟡", "Retention is almost non-existent",
     f"{seg.get('One-time', 0):.1f}% of customers booked once in the month.",
     "Second-ride coupons, post-trip nudges, loyalty tiers; track 30-day repeat rate as a north-star."),
    ("🔵", "Cash still dominates",
     f"Cash {pay.get('Cash', 0):.1f}% · UPI {pay.get('UPI', 0):.1f}% · Cards {pay.get('Credit Card', 0) + pay.get('Debit Card', 0):.1f}%.",
     "UPI cash-back on first 3 rides, reduce cash-handling risk for drivers."),
    ("🟣", "Fares do not track distance",
     f"Fare-distance correlation is {s['Booking_Value'].corr(s['Ride_Distance']):+.3f}; Autos are 10 km avg vs 25 km elsewhere at the same fare.",
     "Audit the fare engine; confirm whether the field is ‘estimated’ or ‘final’ before using it for pricing decisions."),
    ("⚪", "Quality signals are flat",
     f"Ratings avg {k['driver_rating']:.2f} (drivers) / {k['customer_rating']:.2f} (customers); nobody rates below 3.0.",
     "Make ratings more discriminating (tag-based feedback) so they can drive driver coaching."),
]
for icon, head, evidence, action in rows:
    with st.container(border=True):
        a, b = st.columns([1.2, 1])
        a.markdown(f"**{icon} {head}**  \n<span style='color:{C.PALETTE['muted']}'>{evidence}</span>", unsafe_allow_html=True)
        b.markdown(f"**Action:** {action}")

st.divider()
st.subheader("🎚️ Impact simulator")
st.caption("If operations recovered a share of each failure type, how many extra rides and how much revenue is that? "
           "Assumes recovered rides convert at the current average successful fare.")
c = st.columns(3)
r_dc = c[0].slider("Recover driver cancellations", 0, 50, 15, format="%d%%")
r_cc = c[1].slider("Recover customer cancellations", 0, 50, 10, format="%d%%")
r_dnf = c[2].slider("Recover 'driver not found'", 0, 50, 10, format="%d%%")
extra = dc * r_dc / 100 + cc * r_cc / 100 + dnf * r_dnf / 100
extra_rev = extra * fare_avg
new_rate = 100 * (k["successful"] + extra) / n
c = st.columns(3)
ui.kpi(c[0], "Extra rides / month", f"{extra:,.0f}")
ui.kpi(c[1], "Extra revenue / month", ui.inr(extra_rev), extra_rev / k["revenue"] * 100, "%")
ui.kpi(c[2], "New success rate", f"{new_rate:.1f}%", new_rate - k["success_rate"], " pp")

fig = go.Figure(go.Waterfall(
    x=["Current revenue", "Driver cancels", "Customer cancels", "Driver not found", "Projected revenue"],
    measure=["absolute", "relative", "relative", "relative", "total"],
    y=[k["revenue"], dc * r_dc / 100 * fare_avg, cc * r_cc / 100 * fare_avg, dnf * r_dnf / 100 * fare_avg, 0],
    increasing=dict(marker=dict(color=C.PALETTE["good"])), totals=dict(marker=dict(color=C.PALETTE["accent"])),
    connector=dict(line=dict(color="#444"))))
fig.update_layout(yaxis_title="₹", showlegend=False)
ui.show(ui.style(fig, 380, "Revenue bridge (monthly)"))

st.divider()
st.subheader("⚠️ Caveats an experienced analyst would flag")
st.markdown(f"""
* **Synthetic-looking distributions.** Hourly demand, ratings and distances are close to uniform and most pairs of
  numeric columns are uncorrelated. Treat patterns as *directional*; validate on production data before committing budget.
* **One month only** (July 2024) - no seasonality, no trend beyond 31 days.
* **‘Success’ ≠ finished.** {int(s['Incomplete_Rides'].eq('Yes').sum()):,} successful bookings are marked incomplete
  ({k['incomplete_rate']:.1f}%); the brief's "completed rides value" is therefore shown both ways in SQL Q9.
* **Booking value on cancelled rides** is an *intended* fare, not money lost with certainty - the leakage figure is an upper bound.
""")
