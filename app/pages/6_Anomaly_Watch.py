"""Business use-case #4 - detecting anomalies / suspicious activity."""
import numpy as np
import plotly.express as px
import streamlit as st

import ui
from src import analytics as A
from src import config as C

df, fdf, f = ui.setup("Anomaly Watch", "🕵️", "Rule-based fraud & data-integrity screening on the filtered rides")
ui.empty_guard(fdf)
s = fdf[fdf["Is_Success"] == 1]

same = s[s["Flag_Same_Pickup_Drop"] == 1]
fare = s[s["Flag_Fare_Outlier"] == 1]
sc = (fdf[fdf["Booking_Status"] == "Canceled by Customer"].groupby("Customer_ID").size().loc[lambda x: x >= 2])
c = st.columns(4)
ui.kpi(c[0], "Same pickup & drop (successful)", f"{len(same):,}")
ui.kpi(c[1], "Fare-per-km outliers", f"{len(fare):,}")
ui.kpi(c[2], "Serial cancellers", f"{len(sc):,}")
ui.kpi(c[3], "Value at risk", ui.inr(same["Booking_Value"].sum() + fare["Booking_Value"].sum()))
st.write("")

st.markdown(
    "**How the rules work** — *Same pickup & drop*: a completed trip that starts and ends in the same zone but "
    "still bills distance (possible ghost ride or GPS spoofing). *Fare outlier*: fare per km above the Tukey fence "
    "(Q3 + 1.5×IQR on a log scale) for that vehicle type. *Serial canceller*: a customer with 2+ cancellations.")

tab1, tab2, tab3 = st.tabs(["Fare vs distance", "Flagged rides", "Serial cancellers"])
with tab1:
    sample = s.sample(min(8000, len(s)), random_state=7).copy()
    sample["flag"] = np.select([sample["Flag_Fare_Outlier"] == 1, sample["Flag_Same_Pickup_Drop"] == 1],
                               ["Fare outlier", "Same pickup/drop"], "Normal")
    fig = px.scatter(sample, x="Ride_Distance", y="Booking_Value", color="flag", opacity=0.6,
                     color_discrete_map={"Normal": "#30363d", "Fare outlier": C.PALETTE["bad"],
                                         "Same pickup/drop": C.PALETTE["warn"]},
                     hover_data=["Booking_ID", "Vehicle_Type"])
    fig.update_layout(xaxis_title="Distance (km)", yaxis_title="Fare (₹)", legend_title=None)
    ui.show(ui.style(fig, 460, "Fare vs distance (8,000-ride sample)"))
    r = s["Booking_Value"].corr(s["Ride_Distance"])
    st.warning(f"Correlation between fare and distance is **{r:+.3f}**. In a healthy fare model it would be strongly "
               "positive. Fares look decoupled from distance, so *every* long cheap ride and short expensive ride is "
               "a pricing-integrity question - audit the fare engine before acting on individual flags.")
with tab2:
    flagged = s[(s["Flag_Same_Pickup_Drop"] == 1) | (s["Flag_Fare_Outlier"] == 1)].sort_values("Fare_Per_Km", ascending=False)
    cols = ["Booking_ID", "Booking_Date", "Customer_ID", "Vehicle_Type", "Pickup_Location", "Drop_Location",
            "Ride_Distance", "Booking_Value", "Fare_Per_Km", "Flag_Same_Pickup_Drop", "Flag_Fare_Outlier"]
    st.write(f"{len(flagged):,} flagged rides")
    st.dataframe(flagged[cols].head(500), hide_index=True, width="stretch")
    ui.download_df(flagged[cols], "flagged_rides.csv", "⬇️ Download all flagged rides")
with tab3:
    tab = (fdf[fdf["Booking_Status"] == "Canceled by Customer"].groupby("Customer_ID")
           .agg(cancellations=("Booking_ID", "count"), blocked_value=("Booking_Value", "sum"),
                last_cancel=("Booking_Date", "max")).query("cancellations >= 2")
           .sort_values(["cancellations", "blocked_value"], ascending=False))
    st.write(f"{len(tab):,} customers")
    st.dataframe(tab.head(200), width="stretch")
    ui.download_df(tab.reset_index(), "serial_cancellers.csv")
