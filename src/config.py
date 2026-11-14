"""Central configuration: paths, constants and colour palette.

Keeping everything in one place means the ETL, the SQL runner, the tests and the
Streamlit app can never drift apart.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "OLA_DataSet.xlsx"
PROCESSED_DIR = ROOT / "data" / "processed"
CLEAN_CSV = PROCESSED_DIR / "ola_rides_clean.csv"
DB_PATH = PROCESSED_DIR / "ola_rides.db"
DQ_REPORT = ROOT / "docs" / "DATA_QUALITY_REPORT.md"
SQL_DIR = ROOT / "sql"
POWERBI_DIR = ROOT / "powerbi"

# Order used everywhere (matches the slide deck: Prime Sedan ... E-Bike)
VEHICLE_ORDER = ["Prime Sedan", "Prime SUV", "Prime Plus", "Mini", "Auto", "Bike", "E-Bike"]
STATUS_ORDER = ["Success", "Canceled by Customer", "Canceled by Driver", "Driver Not Found"]
DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BAND_ORDER = ["Morning", "Afternoon", "Evening", "Night"]

# Brand-inspired palette (Ola: black / lime-yellow accent)
PALETTE = {
    "bg": "#0E1117",
    "panel": "#161B22",
    "accent": "#D4E600",
    "accent_dark": "#9DAA00",
    "text": "#E6EDF3",
    "muted": "#8B949E",
    "good": "#2EA043",
    "bad": "#F85149",
    "warn": "#D29922",
    "info": "#58A6FF",
}
STATUS_COLORS = {
    "Success": "#2EA043",
    "Canceled by Customer": "#F0883E",
    "Canceled by Driver": "#F85149",
    "Driver Not Found": "#8B949E",
}
VEHICLE_COLORS = dict(
    zip(
        VEHICLE_ORDER,
        ["#D4E600", "#58A6FF", "#BC8CFF", "#2EA043", "#F0883E", "#39D0D8", "#FF7B72"],
    )
)
