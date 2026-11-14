**Power BI Desktop can't be generated as code**, so this folder ships everything needed to build the report in
about 45 minutes: a cleaned data model, 25+ DAX measures, a dark theme and a page-by-page blueprint that follows
the 5 views in the brief (and the `Ola-Slides.pptx` layout).

### 1 · Load the data
1. *Home → Get data → Text/CSV* → `data/processed/ola_rides_clean.csv` → **Transform data**.
   Set `Booking_Timestamp` = *Date/Time*, `Booking_Date` = *Date*, ratings/fare/TAT = *Decimal/Whole*.
2. Load `powerbi/data/dim_vehicle.csv` and `powerbi/data/dim_date.csv`.
3. *Model view* → relationships (many-to-one, single direction):
   * `fact_rides[Vehicle_Type]` → `dim_vehicle[Vehicle_Type]`
   * `fact_rides[Booking_Date]` → `dim_date[Date]`
4. Sort `dim_vehicle[Vehicle_Type]` by `Vehicle_Order`; sort `dim_date[Day_Name]` by `Day_Of_Week`.
5. *View → Themes → Browse for themes* → `powerbi/ola_theme.json`.

*Prefer the database?* Use the MySQL route from the brief: import the CSV into MySQL, then *Get data → MySQL database*.
The SQL in `sql/` is ANSI-friendly (see `docs/SQL_NOTES.md` for the 3 syntax differences).

### 2 · Create measures
Paste each line of `powerbi/measures.dax` into a new measure on a blank `_Measures` table.

### 3 · Pages (one per view in the brief)
| Page | Visuals | Fields |
|---|---|---|
| **1 Overall** | KPI cards (Total Bookings, Success Rate %, Success Booking Value, Avg Fare) · *Line + column* **Ride Volume Over Time** · *Donut* **Booking Status Breakdown** | Axis `dim_date[Date]`; values `[Total Bookings]`, `[Bookings 7D Avg]`; legend `Booking_Status` |
| **2 Vehicle Type** | *Table* with the slide-2 columns · *Bar* **Top 5 Vehicle Types by Ride Distance** (Top N = 5 on `[Total Distance Travelled]`) | `Vehicle_Type`, `[Total Booking Value]`, `[Success Booking Value]`, `[Avg Distance Travelled]`, `[Total Distance Travelled]` |
| **3 Revenue** | *Column* **Revenue by Payment Method** · *Bar* **Top 5 Customers by Total Booking Value** (Top N on `[Total Booking Value]`) · *Box/line* **Ride Distance per Day** | `Payment_Method`, `Customer_ID`, `dim_date[Date]` |
| **4 Cancellation** | Two *bars*: **Cancelled Rides Reasons (Customer)** and **(Driver)** · *Stacked column* **Leakage by vehicle** | `Canceled_Rides_by_Customer`, `Canceled_Rides_by_Driver`, `[Leaked Value]` |
| **5 Ratings** | *Column* **Driver Ratings** distribution · **Customer Ratings** distribution · *Scatter* **Customer vs Driver Rating** by `Vehicle_Type` · vehicle icons (`Icon_URL`, data category *Image URL*) | `Driver_Ratings`, `Customer_Rating`, `[Avg Driver Rating]` |

### 4 · Interactivity checklist
* Slicers (synced across pages via *View → Sync slicers*): **Date**, **Vehicle_Type**, **Booking_Status**, **Day type** (`Is_Weekend`).
* Navigation: the slide deck uses a left-hand menu (Overall · Vehicle Type · Revenue · Cancellation · Ratings) - build it with
  five *Page navigator* buttons, or use *Insert → Buttons → Navigator → Page navigator*.
* Add a *Drill-through* page on `Customer_ID` and a *tooltip page* showing the funnel.
* Bookmarks: "Success only" / "All bookings" toggle for the revenue page.

### 5 · Publish and embed in Streamlit
1. *Home → Publish* to your Power BI workspace (free work account works).
2. In Power BI Service: *File → Embed report → Publish to web (public)* → copy the **link**.
3. Paste it into the **Power BI** page of this app (or save it in `.streamlit/secrets.toml` as `POWERBI_EMBED_URL`).

> "Publish to web" makes the report **public** - fine for this open dataset; never use it for confidential data.
