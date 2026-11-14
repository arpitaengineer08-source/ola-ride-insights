# SQL notes

The queries in `sql/` run on **SQLite** (bundled with Python, zero setup). The brief mentions MySQL + Power BI, so here
is everything that changes if you move the data to MySQL 8 / PostgreSQL. *(Not executed against MySQL in this build -
the SQLite versions are the ones validated by `tests/`.)*

| Topic | SQLite (used here) | MySQL 8 | PostgreSQL |
|---|---|---|---|
| String concat (`a07`) | `a \|\| ' -> ' \|\| b` | `CONCAT(a, ' -> ', b)` | `a \|\| ' -> ' \|\| b` |
| Group by alias (`a08`) | allowed | allowed | use positional / repeat the CASE |
| Window functions / CTEs | yes (>= 3.25) | yes (8.0+) | yes |
| Moving-average frame (`a01`) | `ROWS BETWEEN 6 PRECEDING AND CURRENT ROW` | same | same |

## Load into MySQL (optional)
```python
import pandas as pd
from sqlalchemy import create_engine          # pip install sqlalchemy pymysql
df = pd.read_csv("data/processed/ola_rides_clean.csv")
df.to_sql("rides", create_engine("mysql+pymysql://user:pwd@localhost/ola"), index=False, if_exists="replace", chunksize=5000)
```
Then in Power BI: *Get data → MySQL database* and use the same measures from `powerbi/measures.dax`.

## Design notes
* Column names keep the dataset's original style (`Booking_Status`, `Vehicle_Type` ...) so the brief's wording maps 1:1.
* `Is_Success`, `Is_Completed`, `Cancel_Party`, `Cancel_Reason` are derived once in the ETL, which keeps queries short.
* Indexes exist on status, vehicle, customer, date, payment and pickup columns; `ANALYZE` was run after load.
* **Q2** is shown two ways because the reference sheet averages over *all* bookings (cancelled rides count as 0 km).
* **Q4** has many customers tied at 4 rides, so booking value is used as a documented tie-breaker.
* **Q9** reports both `Success` (₹3.51 Cr) and strictly finished trips (₹3.28 Cr).
