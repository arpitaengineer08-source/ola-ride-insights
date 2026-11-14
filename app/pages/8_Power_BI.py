"""Embed the published Power BI report + hand-off assets."""
import os

import streamlit as st
import streamlit.components.v1 as components

import ui
from src import config as C

ui.setup("Power BI Dashboard", "📊", "Embedded report, build guide and ready-to-load data model", filters=False)

url = ""
try:
    url = st.secrets.get("POWERBI_EMBED_URL", "")
except Exception:  # no secrets file present
    pass
url = url or os.getenv("POWERBI_EMBED_URL", "")
url = st.text_input("Power BI 'Publish to web' embed URL", value=url,
                    placeholder="https://app.powerbi.com/view?r=...",
                    help="Power BI Service → File → Embed report → Publish to web (public). "
                         "Or put it in .streamlit/secrets.toml as POWERBI_EMBED_URL.")
if url.startswith("https://app.powerbi.com/"):
    components.iframe(url, height=720, scrolling=False)
else:
    st.info("Paste your published Power BI link above and the report appears here. "
            "Until then follow the build guide below - it takes about 45 minutes.")

t1, t2, t3 = st.tabs(["🛠️ Build guide", "📐 DAX measures", "📦 Data model files"])
with t1:
    st.markdown((C.POWERBI_DIR / "POWERBI_BUILD_GUIDE.md").read_text(encoding="utf-8"))
with t2:
    st.code((C.POWERBI_DIR / "measures.dax").read_text(encoding="utf-8"), language="sql")
with t3:
    st.markdown("Load these in Power BI (Get data → Text/CSV). Relationships are described in the guide.")
    for label, path in [("Fact table - ola_rides_clean.csv", C.CLEAN_CSV),
                        ("Dimension - dim_vehicle.csv", C.POWERBI_DIR / "data" / "dim_vehicle.csv"),
                        ("Dimension - dim_date.csv", C.POWERBI_DIR / "data" / "dim_date.csv"),
                        ("Theme - ola_theme.json", C.POWERBI_DIR / "ola_theme.json")]:
        st.download_button(f"⬇️ {label}", path.read_bytes(), file_name=path.name, key=path.name)
