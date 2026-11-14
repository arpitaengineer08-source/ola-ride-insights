"""Shared UI helpers: page setup, theme, sidebar filters, KPI cards, plotly styling."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Make `src` importable no matter where VS Code launches Streamlit from.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import analytics as A  # noqa: E402
from src import config as C  # noqa: E402

CSS = f"""
<style>
.block-container {{ padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1400px; }}
h1, h2, h3 {{ letter-spacing: -0.02em; }}
.hero {{ background: linear-gradient(120deg, #161B22 0%, #1d2300 100%); border: 1px solid #2a3000;
        border-radius: 16px; padding: 22px 28px; margin-bottom: 18px; }}
.hero h1 {{ margin: 0; font-size: 2rem; }}
.hero p {{ margin: 4px 0 0; color: {C.PALETTE['muted']}; }}
.kpi {{ background: {C.PALETTE['panel']}; border: 1px solid #262c36; border-radius: 14px; padding: 14px 16px;
        height: 100%; transition: border-color .15s; }}
.kpi:hover {{ border-color: {C.PALETTE['accent']}; }}
.kpi .l {{ color: {C.PALETTE['muted']}; font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }}
.kpi .v {{ font-size: 1.75rem; font-weight: 700; line-height: 1.25; }}
.kpi .d {{ font-size: .8rem; }}
.up {{ color: {C.PALETTE['good']}; }} .down {{ color: {C.PALETTE['bad']}; }} .flat {{ color: {C.PALETTE['muted']}; }}
.ins {{ border-left: 4px solid; border-radius: 8px; padding: 10px 14px; background: {C.PALETTE['panel']}; margin-bottom: 8px; }}
.ins b {{ display: block; margin-bottom: 2px; }}
.ins span {{ color: {C.PALETTE['muted']}; font-size: .88rem; }}
.ins.good {{ border-color: {C.PALETTE['good']}; }} .ins.bad {{ border-color: {C.PALETTE['bad']}; }}
.ins.warn {{ border-color: {C.PALETTE['warn']}; }} .ins.info {{ border-color: {C.PALETTE['info']}; }}
.pill {{ display:inline-block; padding:2px 10px; border-radius:99px; font-size:.75rem; background:#222a33; margin-right:6px; }}
footer {{ visibility: hidden; }}
</style>
"""

# ---- plotly theme ------------------------------------------------------------
_template = go.layout.Template(layout=dict(
    font=dict(family="Inter, Segoe UI, sans-serif", color=C.PALETTE["text"]),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    colorway=list(C.VEHICLE_COLORS.values()),
    xaxis=dict(gridcolor="#222a33", zerolinecolor="#222a33"),
    yaxis=dict(gridcolor="#222a33", zerolinecolor="#222a33"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=10, r=10, t=50, b=10),
))
pio.templates["ola"] = _template
pio.templates.default = "ola"


def style(fig: go.Figure, height: int = 380, title: str | None = None) -> go.Figure:
    fig.update_layout(height=height, title=dict(text=title, x=0, font=dict(size=16)) if title else None)
    return fig


def show(fig: go.Figure, key: str | None = None) -> None:
    st.plotly_chart(fig, width="stretch", key=key, config={"displaylogo": False})


# ---- data (cached) -----------------------------------------------------------
@st.cache_data(show_spinner="Loading rides from SQLite…")
def get_rides() -> pd.DataFrame:
    return A.load_rides()


@st.cache_data(show_spinner=False)
def get_vehicle_dim() -> pd.DataFrame:
    return A.load_vehicle_dim()


# ---- page setup + sidebar filters -------------------------------------------
_FILTER_KEYS = {"f_dates": None, "f_veh": None, "f_status": None, "f_day": "All"}


def _sticky(key: str, default):
    """Streamlit drops widget state when you change page; mirror it in a plain key."""
    store = f"_keep_{key}"
    if store in st.session_state:
        st.session_state[key] = st.session_state[store]
    elif key not in st.session_state:
        st.session_state[key] = default


def _remember(key: str):
    st.session_state[f"_keep_{key}"] = st.session_state[key]


def setup(title: str, icon: str, subtitle: str = "", filters: bool = True):
    """Call first on every page. Returns (all_rides, filtered_rides, Filters|None)."""
    st.set_page_config(page_title=f"{title} · Ola Ride Insights", page_icon=icon, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(f'<div class="hero"><h1>{icon} {title}</h1><p>{subtitle}</p></div>', unsafe_allow_html=True)
    df = get_rides()
    if not filters:
        return df, df, None

    lo, hi = df["Booking_Date"].min().date(), df["Booking_Date"].max().date()
    _sticky("f_dates", (lo, hi))
    _sticky("f_veh", list(C.VEHICLE_ORDER))
    _sticky("f_status", list(C.STATUS_ORDER))
    _sticky("f_day", "All")

    with st.sidebar:
        st.markdown("### 🎛️ Global filters")
        dates = st.date_input("Date range", min_value=lo, max_value=hi, key="f_dates",
                              on_change=_remember, args=("f_dates",))
        st.multiselect("Vehicle type", C.VEHICLE_ORDER, key="f_veh", on_change=_remember, args=("f_veh",))
        st.multiselect("Booking status", C.STATUS_ORDER, key="f_status", on_change=_remember, args=("f_status",))
        st.radio("Day type", ["All", "Weekday", "Weekend"], key="f_day", horizontal=True,
                 on_change=_remember, args=("f_day",))
        if st.button("Reset filters", width="stretch"):
            for k in list(st.session_state):
                if k.startswith(("f_", "_keep_f_")):
                    del st.session_state[k]
            st.rerun()

    start, end = (dates if isinstance(dates, (tuple, list)) and len(dates) == 2 else (lo, hi))
    f = A.Filters(pd.Timestamp(start), pd.Timestamp(end), tuple(st.session_state["f_veh"]),
                  tuple(st.session_state["f_status"]), st.session_state["f_day"])
    fdf = A.apply_filters(df, f)
    with st.sidebar:
        st.caption(f"**{len(fdf):,}** of {len(df):,} bookings selected")
        st.caption("Data: OLA bookings · Bengaluru · July 2024")
    return df, fdf, f


# ---- components --------------------------------------------------------------
def kpi(col, label: str, value: str, delta: float | None = None, suffix: str = "", invert: bool = False):
    cls, arrow, txt = "flat", "", ""
    if delta is not None and pd.notna(delta):
        good = (delta > 0) != invert
        cls = "flat" if abs(delta) < 0.05 else ("up" if good else "down")
        arrow = "▲" if delta > 0 else "▼"
        txt = f'<div class="d {cls}">{arrow} {abs(delta):.1f}{suffix} vs prev. 7 days</div>'
    col.markdown(f'<div class="kpi"><div class="l">{label}</div><div class="v">{value}</div>{txt}</div>',
                 unsafe_allow_html=True)


def insight_cards(items) -> None:
    for i in items:
        st.markdown(f'<div class="ins {i.tone}"><b>{i.title}</b><span>{i.body}</span></div>', unsafe_allow_html=True)


def inr(x: float) -> str:
    return A._inr(x)


def empty_guard(fdf: pd.DataFrame) -> None:
    if fdf.empty:
        st.warning("No rides match the current filters. Widen the filters in the sidebar.")
        st.stop()


def download_df(df: pd.DataFrame, name: str, label: str = "⬇️ Download CSV") -> None:
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=name, mime="text/csv")
