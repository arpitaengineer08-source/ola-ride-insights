"""Pure-pandas analytics layer. No Streamlit imports -> fully unit-testable.

Every number shown in the dashboard is produced here (or by the SQL files), so the
KPI definitions live in exactly one place.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import config as C
from src import db


# --------------------------------------------------------------------------- #
# Loading & filtering
# --------------------------------------------------------------------------- #
def load_rides() -> pd.DataFrame:
    """Load the fact table from SQLite with proper dtypes."""
    with db.connect() as con:
        df = pd.read_sql_query("SELECT * FROM rides", con, parse_dates=["Booking_Timestamp"])
    df["Booking_Date"] = pd.to_datetime(df["Booking_Date"])
    for col, order in {
        "Vehicle_Type": C.VEHICLE_ORDER, "Booking_Status": C.STATUS_ORDER,
        "Day_Name": C.DAY_ORDER, "Time_Band": C.BAND_ORDER,
    }.items():
        df[col] = pd.Categorical(df[col], categories=order, ordered=True)
    return df


def load_vehicle_dim() -> pd.DataFrame:
    return db.run_sql("SELECT * FROM dim_vehicle ORDER BY Vehicle_Order")


@dataclass(frozen=True)
class Filters:
    start: pd.Timestamp
    end: pd.Timestamp
    vehicles: tuple[str, ...]
    statuses: tuple[str, ...]
    day_type: str = "All"          # All | Weekday | Weekend


def apply_filters(df: pd.DataFrame, f: Filters) -> pd.DataFrame:
    m = df["Booking_Date"].between(f.start, f.end)
    m &= df["Vehicle_Type"].isin(f.vehicles) & df["Booking_Status"].isin(f.statuses)
    if f.day_type == "Weekday":
        m &= df["Is_Weekend"].eq(0)
    elif f.day_type == "Weekend":
        m &= df["Is_Weekend"].eq(1)
    return df.loc[m]


# --------------------------------------------------------------------------- #
# KPI definitions
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame) -> dict[str, float]:
    n = len(df)
    s = df[df["Is_Success"] == 1]
    return {
        "bookings": n,
        "successful": len(s),
        "success_rate": 100 * len(s) / n if n else np.nan,
        "cancel_rate": 100 * df["Booking_Status"].isin(["Canceled by Customer", "Canceled by Driver"]).mean() if n else np.nan,
        "dnf_rate": 100 * df["Booking_Status"].eq("Driver Not Found").mean() if n else np.nan,
        "revenue": s["Booking_Value"].sum(),
        "leaked": df.loc[df["Is_Success"] == 0, "Booking_Value"].sum(),
        "avg_fare": s["Booking_Value"].mean(),
        "avg_distance": s["Ride_Distance"].mean(),
        "total_distance": s["Ride_Distance"].sum(),
        "driver_rating": s["Driver_Ratings"].mean(),
        "customer_rating": s["Customer_Rating"].mean(),
        "incomplete_rate": 100 * s["Incomplete_Rides"].eq("Yes").mean() if len(s) else np.nan,
        "customers": df["Customer_ID"].nunique(),
    }


def period_delta(df: pd.DataFrame, days: int = 7) -> dict[str, float]:
    """Last `days` vs the `days` before, on the *filtered* data (percentage-point or % change)."""
    if df.empty:
        return {}
    end = df["Booking_Date"].max()
    cur = df[df["Booking_Date"] > end - pd.Timedelta(days=days)]
    prev = df[(df["Booking_Date"] <= end - pd.Timedelta(days=days)) &
              (df["Booking_Date"] > end - pd.Timedelta(days=2 * days))]
    if prev.empty:
        return {}
    a, b = kpis(cur), kpis(prev)
    pct = lambda k: 100 * (a[k] - b[k]) / b[k] if b[k] else np.nan
    return {"bookings": pct("bookings"), "revenue": pct("revenue"),
            "success_rate": a["success_rate"] - b["success_rate"], "avg_fare": pct("avg_fare")}


# --------------------------------------------------------------------------- #
# Aggregations used by several pages
# --------------------------------------------------------------------------- #
def daily_series(df: pd.DataFrame) -> pd.DataFrame:
    g = (df.assign(revenue=df["Booking_Value"].where(df["Is_Success"] == 1, 0))
           .groupby("Booking_Date", observed=True)
           .agg(bookings=("Booking_ID", "count"), successful=("Is_Success", "sum"), revenue=("revenue", "sum"))
           .reset_index())
    g["bookings_ma7"] = g["bookings"].rolling(7, min_periods=1).mean()
    g["success_rate"] = 100 * g["successful"] / g["bookings"]
    return g


def status_by_day(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby(["Booking_Date", "Booking_Status"], observed=True).size()
              .rename("rides").reset_index())


def funnel(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    found = total - int(df["Booking_Status"].eq("Driver Not Found").sum())
    success = int(df["Is_Success"].sum())
    completed = int(df["Is_Completed"].sum())
    return pd.DataFrame({"stage": ["Bookings placed", "Driver found", "Not cancelled (Success)", "Trip completed"],
                         "rides": [total, found, success, completed]})


def vehicle_summary(df: pd.DataFrame) -> pd.DataFrame:
    s = df[df["Is_Success"] == 1]
    g = df.groupby("Vehicle_Type", observed=True).agg(
        bookings=("Booking_ID", "count"), total_booking_value=("Booking_Value", "sum"))
    g["success_booking_value"] = s.groupby("Vehicle_Type", observed=True)["Booking_Value"].sum()
    g["avg_distance_km"] = s.groupby("Vehicle_Type", observed=True)["Ride_Distance"].mean()
    g["total_distance_km"] = s.groupby("Vehicle_Type", observed=True)["Ride_Distance"].sum()
    g["avg_fare"] = s.groupby("Vehicle_Type", observed=True)["Booking_Value"].mean()
    g["success_rate"] = 100 * df.groupby("Vehicle_Type", observed=True)["Is_Success"].mean()
    g[["success_booking_value", "total_distance_km"]] = g[["success_booking_value", "total_distance_km"]].fillna(0)
    g["driver_rating"] = s.groupby("Vehicle_Type", observed=True)["Driver_Ratings"].mean()
    g["customer_rating"] = s.groupby("Vehicle_Type", observed=True)["Customer_Rating"].mean()
    return g.reset_index()


def demand_heatmap(df: pd.DataFrame, per_day: bool = True) -> pd.DataFrame:
    """Weekday x hour matrix. per_day=True divides by how often that weekday occurs."""
    h = df.groupby(["Day_Name", "Booking_Hour"], observed=True).size().unstack(fill_value=0)
    h = h.reindex(C.DAY_ORDER).reindex(columns=range(24), fill_value=0)
    if per_day:
        n_days = df.drop_duplicates("Booking_Date").groupby("Day_Name", observed=True).size().reindex(C.DAY_ORDER)
        h = h.div(n_days, axis=0)
    return h


def customer_segments(df: pd.DataFrame) -> pd.DataFrame:
    per = df.groupby("Customer_ID").agg(rides=("Booking_ID", "count"), value=("Booking_Value", "sum"))
    seg = pd.cut(per["rides"], [0, 1, 2, np.inf], labels=["One-time", "Occasional (2)", "Frequent (3+)"])
    out = per.groupby(seg, observed=True).agg(customers=("rides", "size"), value=("value", "sum")).reset_index()
    out["pct_customers"] = 100 * out["customers"] / out["customers"].sum()
    return out.rename(columns={"rides": "segment"})


# --------------------------------------------------------------------------- #
# Insight engine - turns the filtered data into plain-English findings
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Insight:
    tone: str      # good | warn | bad | info
    title: str
    body: str


def _inr(x: float) -> str:
    if x >= 1e7:
        return f"₹{x / 1e7:.2f} Cr"
    if x >= 1e5:
        return f"₹{x / 1e5:.2f} L"
    return f"₹{x:,.0f}"


def generate_insights(df: pd.DataFrame) -> list[Insight]:
    if df.empty:
        return [Insight("warn", "No data", "The current filters return no rides.")]
    k = kpis(df)
    out: list[Insight] = []

    out.append(Insight(
        "bad" if k["success_rate"] < 70 else "good",
        f"Only {k['success_rate']:.1f}% of bookings become rides",
        f"{_inr(k['leaked'])} of booking value ({100 * k['leaked'] / (k['leaked'] + k['revenue']):.1f}%) "
        "was lost to cancellations and unmatched requests."))

    c = df[df["Cancel_Reason"].notna()]
    if not c.empty:
        top = c.groupby(["Cancel_Party", "Cancel_Reason"]).size().sort_values(ascending=False)
        (party, reason), n = next(iter(top.items()))
        out.append(Insight("warn", f"Top fixable cancel reason: “{reason}”",
                           f"{n:,} cancellations by the {party.lower()} ({100 * n / len(c):.1f}% of all cancels). "
                           + ("Driver-side causes are controllable through vehicle checks, incentives and smarter dispatch."
                              if party == "Driver" else
                              "Customer-side causes point to ETA accuracy and live-tracking trust.")))

    s = df[df["Is_Success"] == 1]
    if not s.empty:
        pay = s["Payment_Method"].value_counts(normalize=True) * 100
        out.append(Insight("info", f"{pay.index[0]} still leads payments ({pay.iloc[0]:.1f}%)",
                           f"UPI is at {pay.get('UPI', 0):.1f}%, cards at just "
                           f"{pay.get('Credit Card', 0) + pay.get('Debit Card', 0):.1f}% - "
                           "a clear lever for cashless incentives."))
        auto, others = s[s["Vehicle_Type"] == "Auto"], s[s["Vehicle_Type"] != "Auto"]
        if len(auto) and len(others):
            out.append(Insight("info", "Autos are the short-hop product",
                               f"Average Auto trip is {auto['Ride_Distance'].mean():.1f} km vs "
                               f"{others['Ride_Distance'].mean():.1f} km for other vehicles, yet the average fare is "
                               f"similar ({_inr(auto['Booking_Value'].mean())} vs {_inr(others['Booking_Value'].mean())}) - "
                               "Autos earn far more per km."))
        r = s["Booking_Value"].corr(s["Ride_Distance"])
        if abs(r) < 0.1:
            out.append(Insight("warn", "Fares are not driven by distance",
                               f"Correlation between fare and distance is {r:+.2f}. Either pricing is dominated by "
                               "surge/base fares or the fare field needs auditing."))

    cust = customer_segments(df)
    one = cust.loc[cust["segment"].astype(str) == "One-time", "pct_customers"]
    if len(one):
        out.append(Insight("warn", f"{one.iloc[0]:.1f}% of customers booked only once",
                           "Retention is the biggest growth lever: second-ride coupons and win-back nudges."))

    d = daily_series(df)
    if len(d) > 3:
        out.append(Insight("info", f"Best day: {d.loc[d['bookings'].idxmax(), 'Booking_Date']:%d %b}",
                           f"{int(d['bookings'].max()):,} bookings vs a {d['bookings'].mean():,.0f} daily average "
                           f"(spread is only ±{100 * d['bookings'].std() / d['bookings'].mean():.1f}% - demand is very even)."))
    return out
