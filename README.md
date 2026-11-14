# 🚕 Ola Ride Insights

End-to-end ride-sharing analytics: **data cleaning → SQL → Streamlit dashboard → Power BI kit → business storytelling.**
103,024 Bengaluru bookings (July 2024) · 7 vehicle types · 4 booking outcomes.

## ▶ Run it in VS Code (2 minutes)

1. Unzip, then **File → Open Folder** → `ola-ride-insights`.
2. Open the terminal (`Ctrl + ~`) and run:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python -m src.etl                 # builds data/processed/ola_rides.db from the raw Excel
streamlit run app/streamlit_app.py
```
Build the SQLite database once (~1 min, it is not stored in git): `python -m src.etl`

The browser opens at http://localhost:8501.
Shortcut: double-click `run.bat` (Windows) or run `./run.sh` (macOS/Linux). Press **F5** to debug (launch configs included).

Optional: `python -m src.etl` rebuilds everything from the raw Excel (~1 min) · `pytest` runs 46 tests (~25 s).
Requires Python 3.10+.

## What is inside

| Folder | Purpose |
|---|---|
| `app/` | Streamlit app - 10 pages |
| `src/` | `etl.py` (clean + validate + load), `db.py` (safe SQL layer), `analytics.py` (KPIs, insight engine), `config.py` |
| `sql/` | `01_assignment_queries.sql` (the 10 brief questions) · `02_advanced_analytics.sql` (14 extra) |
| `powerbi/` | cleaned star-schema CSVs, `measures.dax` (25+ measures), dark theme JSON, page-by-page build guide |
| `notebooks/` | `01_EDA.ipynb` - executed EDA with charts |
| `tests/` | SQL-vs-raw-Excel validation + app-layer tests |
| `docs/` | `DATA_QUALITY_REPORT.md` (auto-generated), `INSIGHTS.md`, `SQL_NOTES.md` |
| `data/` | `raw/` original Excel · `processed/` clean CSV + `ola_rides.db` |

## App pages
| Page | Highlights |
|---|---|
| **Overall** | 12 KPIs with 7-day deltas, auto-generated insights, booking funnel, volume (daily/hourly/weekday), status donut, demand heat-map |
| **Vehicle Type** | Slide-2 scorecard with icons, top-5 by distance, distance-vs-fare bubble, outcome mix, rating cards |
| **Revenue** | realised vs gross toggle, payment mix, top-5 customers, distance per day, cumulative revenue |
| **Cancellation** | customer vs driver reasons, failure by hour, revenue leakage, pickup hot-spots, serial cancellers |
| **Ratings** | distributions, vehicle comparison, customer-vs-driver density |
| **SQL Lab** | all 24 queries live + safe free-form SQL editor + schema browser |
| **Anomaly Watch** | same pickup/drop, fare-per-km outliers, serial cancellers, exportable watch-list |
| **Data Explorer** | search by Booking/Customer ID, filters, CSV export |
| **Power BI** | embed your published report + build guide + DAX + data files |
| **Executive Brief** | findings → actions, **what-if impact simulator**, caveats |

Global sidebar filters (date, vehicle, status, weekday/weekend) persist across pages.

## What makes it different
* **Validated, not assumed** - 12 integrity checks at load time; every brief SQL answer is cross-checked against the raw Excel in `tests/`.
* **Honest analysis** - flags where the data looks synthetic (uniform demand/ratings, fare ≠ distance) instead of inventing patterns.
* **Ambiguities resolved explicitly** - Q2 (all vs successful bookings), Q4 (ties), Q9 ("Success" vs strictly completed) each shown both ways.
* **Insight engine + simulator** - text findings regenerate from filters; the simulator prices the value of fixing cancellations.
* **Safe SQL console** - read-only connection, single statement, keyword guard, row cap.
* **Production habits** - config module, typed code, star schema, indexes, views, logging, tests, VS Code launch/tasks.

## ⚠️ Power BI note
A `.pbix` cannot be generated outside Power BI Desktop. `powerbi/` contains everything to build it quickly
(see `powerbi/POWERBI_BUILD_GUIDE.md`). After publishing, paste the link in the app's **Power BI** page or in `.streamlit/secrets.toml`.

## Data definitions
`Success` = booking not cancelled and driver found (63,967). `Is_Completed` = Success **and** not incomplete (60,041).
Booking value on cancelled rides is the *intended* fare. Full list of cleaning decisions: `docs/DATA_QUALITY_REPORT.md`.
