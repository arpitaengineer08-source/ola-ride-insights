"""ETL pipeline: raw Excel -> validated, enriched dataset -> CSV + SQLite.

Run:  python -m src.etl

Design choices (all documented in docs/DATA_QUALITY_REPORT.md):
* Structural NULLs are *kept* as NULL (e.g. a cancelled ride has no rating). They are
  information, not noise; imputing them would corrupt averages.
* Labels are standardised (``eBike`` -> ``E-Bike`` to match the dashboard brief).
* Feature engineering adds time, fare-efficiency and anomaly-flag columns.
* The vehicle icon URL (repeated 103k times) is normalised into ``dim_vehicle``.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src import config as C

log = logging.getLogger("ola.etl")

VEHICLE_FIX = {"eBike": "E-Bike", "Ebike": "E-Bike", "E-bike": "E-Bike"}


# --------------------------------------------------------------------------- #
# Extract
# --------------------------------------------------------------------------- #
def extract(path=C.RAW_XLSX) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read the main sheet ('July') and the vehicle icon lookup ('Sheet2')."""
    log.info("Reading %s (this takes ~30-60 s for 100k rows)...", path.name)
    rides = pd.read_excel(path, sheet_name="July")
    icons = pd.read_excel(path, sheet_name="Sheet2", header=None, names=["Vehicle_Type", "Icon_URL"])
    icons = icons.dropna().reset_index(drop=True)
    return rides, icons


# --------------------------------------------------------------------------- #
# Transform
# --------------------------------------------------------------------------- #
@dataclass
class QualityReport:
    """Collects every check so the report is generated, not hand-written."""

    rows_raw: int = 0
    rows_clean: int = 0
    checks: list[tuple[str, bool, str]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.checks.append((name, bool(ok), detail))
        (log.info if ok else log.warning)("%s %s %s", "PASS" if ok else "FAIL", name, detail)


def _time_band(hour: pd.Series) -> pd.Series:
    bands = pd.cut(
        hour,
        bins=[-1, 5, 11, 16, 21, 23],
        labels=["Night", "Morning", "Afternoon", "Evening", "Night "],
        ordered=False,
    )
    return bands.astype(str).str.strip()


def transform(raw: pd.DataFrame, icons: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, QualityReport]:
    q = QualityReport(rows_raw=len(raw))
    df = raw.copy()

    # ---- 1. tidy text columns -------------------------------------------------
    obj_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in obj_cols:
        df[col] = df[col].astype("string").str.strip()
    df["Vehicle_Type"] = df["Vehicle_Type"].replace(VEHICLE_FIX)
    icons["Vehicle_Type"] = icons["Vehicle_Type"].replace(VEHICLE_FIX)

    # ---- 2. integrity checks on the *raw* data -------------------------------
    q.check("Booking_ID is unique", df["Booking_ID"].is_unique, f"{df['Booking_ID'].nunique():,} unique IDs")
    q.check("No fully duplicated rows", df.duplicated().sum() == 0)
    q.check("Booking_Value strictly positive", (df["Booking_Value"] > 0).all(),
            f"range {df['Booking_Value'].min()}-{df['Booking_Value'].max()}")
    q.check("Ratings within 1-5", df[["Driver_Ratings", "Customer_Rating"]].stack().dropna().between(1, 5).all(),
            f"observed {df['Driver_Ratings'].min()}-{df['Driver_Ratings'].max()}")
    q.check("Dates all inside July 2024",
            df["Date"].between("2024-07-01", "2024-07-31 23:59:59").all())

    status = df["Booking_Status"]
    is_succ = status.eq("Success")
    q.check("Cancel-by-customer reason present iff status = 'Canceled by Customer'",
            df["Canceled_Rides_by_Customer"].notna().eq(status.eq("Canceled by Customer")).all())
    q.check("Cancel-by-driver reason present iff status = 'Canceled by Driver'",
            df["Canceled_Rides_by_Driver"].notna().eq(status.eq("Canceled by Driver")).all())
    q.check("Ratings/payment/TAT present only for successful rides",
            df[["Driver_Ratings", "Customer_Rating", "Payment_Method", "V_TAT", "C_TAT"]]
            .notna().all(axis=1).eq(is_succ).all())
    q.check("Ride_Distance = 0 for every non-successful booking", (df.loc[~is_succ, "Ride_Distance"] == 0).all())
    q.check("Incomplete reason present iff Incomplete_Rides = 'Yes'",
            df["Incomplete_Rides_Reason"].notna().eq(df["Incomplete_Rides"].eq("Yes")).all())
    q.check("Date timestamp matches the separate Time column",
            (df["Date"].dt.strftime("%H:%M:%S") == df["Time"].astype(str)).all())

    # ---- 3. feature engineering ---------------------------------------------
    ts = df["Date"]
    df["Booking_Timestamp"] = ts
    df["Booking_Date"] = ts.dt.strftime("%Y-%m-%d")
    df["Booking_Time"] = df["Time"].astype(str)
    df["Booking_Hour"] = ts.dt.hour
    df["Day_Name"] = ts.dt.day_name()
    df["Day_Of_Week"] = ts.dt.dayofweek + 1                      # Mon=1 ... Sun=7
    df["Week_Of_Month"] = ((ts.dt.day - 1) // 7 + 1).clip(upper=5)
    df["Is_Weekend"] = (ts.dt.dayofweek >= 5).astype(int)
    df["Time_Band"] = _time_band(df["Booking_Hour"])

    df["Is_Success"] = is_succ.astype(int)
    df["Is_Incomplete"] = df["Incomplete_Rides"].map({"Yes": 1, "No": 0}).astype("Int64")
    df["Is_Completed"] = (is_succ & df["Incomplete_Rides"].eq("No")).astype(int)
    df["Cancel_Party"] = np.select(
        [status.eq("Canceled by Customer"), status.eq("Canceled by Driver"), status.eq("Driver Not Found")],
        ["Customer", "Driver", "No Driver"], default=None)
    df["Cancel_Reason"] = df["Canceled_Rides_by_Customer"].fillna(df["Canceled_Rides_by_Driver"])
    df["Fare_Per_Km"] = (df["Booking_Value"] / df["Ride_Distance"].replace(0, np.nan)).round(2)

    # ---- 4. anomaly flags (business use-case #4: fraud / anomaly detection) --
    same = df["Pickup_Location"].eq(df["Drop_Location"])
    df["Flag_Same_Pickup_Drop"] = (same & is_succ).astype(int)

    # Robust fare/km outlier per vehicle type: Tukey fence on log scale (fare/km is heavy-tailed)
    lf = np.log(df["Fare_Per_Km"])
    stats = lf[is_succ].groupby(df["Vehicle_Type"]).quantile([0.25, 0.75]).unstack()
    upper = stats[0.75] + 1.5 * (stats[0.75] - stats[0.25])
    df["Flag_Fare_Outlier"] = (is_succ & (lf > df["Vehicle_Type"].map(upper))).astype(int)

    # Auto-rickshaw distance is capped at 19 km - flag nothing, but record the finding
    auto_max = df.loc[df["Vehicle_Type"].eq("Auto") & is_succ, "Ride_Distance"].max()
    q.notes.append(f"Auto rides never exceed {auto_max} km, while every other vehicle reaches 49 km "
                   "(likely a business rule, e.g. city-limit permit).")
    corr = df.loc[is_succ, ["Booking_Value", "Ride_Distance"]].corr().iloc[0, 1]
    q.notes.append(f"Booking_Value vs Ride_Distance correlation on successful rides is {corr:+.3f} - "
                   "fares are essentially independent of distance in this dataset (pricing red flag).")
    q.notes.append(f"{int(df['Flag_Same_Pickup_Drop'].sum()):,} successful rides have identical pickup and drop "
                   "location (flagged, not removed).")
    q.notes.append(f"{int(df['Flag_Fare_Outlier'].sum()):,} successful rides flagged as fare-per-km outliers "
                   "(Tukey fence on log scale, per vehicle type).")

    # ---- 5. final tidy-up -----------------------------------------------------
    df = df.drop(columns=["Date", "Time", "Vehicle Images"])
    ordered = [
        "Booking_ID", "Booking_Timestamp", "Booking_Date", "Booking_Time", "Booking_Hour", "Day_Name",
        "Day_Of_Week", "Week_Of_Month", "Is_Weekend", "Time_Band", "Customer_ID", "Vehicle_Type",
        "Booking_Status", "Is_Success", "Is_Completed", "Pickup_Location", "Drop_Location",
        "Ride_Distance", "Booking_Value", "Fare_Per_Km", "Payment_Method", "V_TAT", "C_TAT",
        "Driver_Ratings", "Customer_Rating", "Canceled_Rides_by_Customer", "Canceled_Rides_by_Driver",
        "Cancel_Party", "Cancel_Reason", "Incomplete_Rides", "Incomplete_Rides_Reason", "Is_Incomplete",
        "Flag_Same_Pickup_Drop", "Flag_Fare_Outlier",
    ]
    df = df[ordered].sort_values("Booking_Timestamp").reset_index(drop=True)
    q.rows_clean = len(df)
    q.check("No rows lost during cleaning", q.rows_raw == q.rows_clean, f"{q.rows_raw:,} -> {q.rows_clean:,}")

    dim_vehicle = (icons.drop_duplicates("Vehicle_Type")
                   .assign(Vehicle_Order=lambda d: d["Vehicle_Type"].map({v: i for i, v in enumerate(C.VEHICLE_ORDER, 1)}))
                   .sort_values("Vehicle_Order").reset_index(drop=True))
    return df, dim_vehicle, q


# --------------------------------------------------------------------------- #
# Load
# --------------------------------------------------------------------------- #
INDEXES = {
    "idx_rides_status": "Booking_Status",
    "idx_rides_vehicle": "Vehicle_Type",
    "idx_rides_customer": "Customer_ID",
    "idx_rides_date": "Booking_Date",
    "idx_rides_payment": "Payment_Method",
    "idx_rides_pickup": "Pickup_Location",
}


def load(df: pd.DataFrame, dim_vehicle: pd.DataFrame) -> None:
    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(C.CLEAN_CSV, index=False)
    C.POWERBI_DIR.joinpath("data").mkdir(exist_ok=True)
    dim_vehicle.to_csv(C.POWERBI_DIR / "data" / "dim_vehicle.csv", index=False)
    build_dim_date(df).to_csv(C.POWERBI_DIR / "data" / "dim_date.csv", index=False)

    if C.DB_PATH.exists():
        C.DB_PATH.unlink()
    with sqlite3.connect(C.DB_PATH) as con:
        out = df.copy()
        out["Booking_Timestamp"] = out["Booking_Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        out.to_sql("rides", con, index=False)
        dim_vehicle.to_sql("dim_vehicle", con, index=False)
        con.execute("CREATE UNIQUE INDEX idx_rides_pk ON rides(Booking_ID)")
        for name, col in INDEXES.items():
            con.execute(f"CREATE INDEX {name} ON rides({col})")
        con.executescript(VIEWS_SQL)
        con.execute("ANALYZE")
    log.info("Wrote %s and %s", C.CLEAN_CSV.name, C.DB_PATH.name)


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    d = pd.DataFrame({"Date": pd.date_range(df["Booking_Timestamp"].min().normalize(),
                                            df["Booking_Timestamp"].max().normalize())})
    d["Day"] = d["Date"].dt.day
    d["Day_Name"] = d["Date"].dt.day_name()
    d["Day_Of_Week"] = d["Date"].dt.dayofweek + 1
    d["Week_Of_Month"] = ((d["Day"] - 1) // 7 + 1).clip(upper=5)
    d["Is_Weekend"] = (d["Day_Of_Week"] >= 6).astype(int)
    d["Month"] = d["Date"].dt.strftime("%B")
    d["Year"] = d["Date"].dt.year
    return d


# Analytical views: keep the app/Power BI queries short and consistent.
VIEWS_SQL = """
DROP VIEW IF EXISTS v_successful_rides;
CREATE VIEW v_successful_rides AS
    SELECT * FROM rides WHERE Booking_Status = 'Success';

DROP VIEW IF EXISTS v_cancellations;
CREATE VIEW v_cancellations AS
    SELECT Booking_ID, Booking_Date, Vehicle_Type, Booking_Status, Cancel_Party, Cancel_Reason,
           Pickup_Location, Booking_Value, Customer_ID
    FROM rides WHERE Booking_Status <> 'Success';

DROP VIEW IF EXISTS v_daily_kpis;
CREATE VIEW v_daily_kpis AS
    SELECT Booking_Date,
           COUNT(*)                                                    AS total_bookings,
           SUM(Is_Success)                                             AS successful,
           ROUND(100.0 * SUM(Is_Success) / COUNT(*), 2)                AS success_rate_pct,
           SUM(CASE WHEN Is_Success = 1 THEN Booking_Value ELSE 0 END) AS revenue
    FROM rides GROUP BY Booking_Date;
"""


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def write_report(df: pd.DataFrame, q: QualityReport) -> None:
    nulls = df.isna().sum()
    nulls = nulls[nulls > 0]
    lines = [
        "# Data Quality Report",
        "",
        "_Auto-generated by `python -m src.etl` - do not edit by hand._",
        "",
        f"* **Rows in / out:** {q.rows_raw:,} -> {q.rows_clean:,}",
        f"* **Period:** {df['Booking_Date'].min()} to {df['Booking_Date'].max()}",
        f"* **Columns after feature engineering:** {df.shape[1]}",
        "",
        "## Validation checks",
        "",
        "| # | Check | Result | Detail |",
        "|---|-------|--------|--------|",
    ]
    for i, (name, ok, detail) in enumerate(q.checks, 1):
        lines.append(f"| {i} | {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines += ["", "## Structural NULLs (kept on purpose)", "",
              "| Column | NULL count | Why |", "|---|---|---|"]
    why = {
        "Payment_Method": "No payment is taken unless the ride is successful",
        "Driver_Ratings": "Only completed trips are rated", "Customer_Rating": "Only completed trips are rated",
        "V_TAT": "Vehicle turnaround time exists only for matched, successful rides",
        "C_TAT": "Customer turnaround time exists only for matched, successful rides",
        "Canceled_Rides_by_Customer": "Populated only when the customer cancelled",
        "Canceled_Rides_by_Driver": "Populated only when the driver cancelled",
        "Cancel_Party": "Populated only for non-successful bookings",
        "Cancel_Reason": "Populated only for customer/driver cancellations",
        "Incomplete_Rides": "Evaluated only for successful bookings",
        "Is_Incomplete": "Evaluated only for successful bookings",
        "Incomplete_Rides_Reason": "Populated only when a successful booking ended incomplete",
        "Fare_Per_Km": "Undefined when distance = 0 (non-successful bookings)",
    }
    for col, n in nulls.items():
        lines.append(f"| {col} | {n:,} | {why.get(col, '')} |")
    lines += ["", "## Data-driven observations", ""] + [f"* {n}" for n in q.notes]
    lines += ["", "## Cleaning decisions", "",
              "1. Whitespace trimmed on every text column; `eBike` standardised to `E-Bike`.",
              "2. `Date` held a full timestamp, so `Time` was redundant; both were reconciled and a single "
              "`Booking_Timestamp` kept, plus derived hour / weekday / time-band columns.",
              "3. Vehicle icon URLs moved to `dim_vehicle` (star-schema, saves ~7 MB).",
              "4. `Success` does **not** mean the ride was finished: 3,926 successful bookings are flagged "
              "`Incomplete_Rides = 'Yes'`. `Is_Completed` captures strict completion.",
              "5. No imputation was performed; no row was dropped."]
    C.DQ_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    argparse.ArgumentParser(description="Build the cleaned Ola dataset and SQLite DB").parse_args()
    raw, icons = extract()
    df, dim_vehicle, q = transform(raw, icons)
    load(df, dim_vehicle)
    write_report(df, q)
    failed = [c for c in q.checks if not c[1]]
    if failed:
        raise SystemExit(f"{len(failed)} data-quality check(s) failed - see log")
    log.info("ETL finished OK")


if __name__ == "__main__":
    main()
