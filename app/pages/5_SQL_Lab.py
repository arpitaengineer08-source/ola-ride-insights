"""SQL Lab - run every query from /sql, or write your own (read-only)."""
import pandas as pd
import streamlit as st

import ui
from src import db

df, _, _ = ui.setup("SQL Lab", "🧪", "All 10 brief questions + 14 advanced queries, running live on SQLite", filters=False)

queries = db.all_queries()
assignment = [q for q in queries.values() if q.id.startswith("q")]
advanced = [q for q in queries.values() if q.id.startswith("a")]

tab1, tab2, tab3 = st.tabs(["📝 Brief questions (Q1-Q10)", "🚀 Advanced analytics", "⌨️ Free-form SQL"])


def render(group, key):
    labels = {q.id: f"{q.id.upper()} · {q.title}" for q in group}
    qid = st.selectbox("Choose a query", list(labels), format_func=labels.get, key=key)
    q = queries[qid]
    if q.note:
        st.info(q.note)
    st.code(q.sql, language="sql")
    res = db.run_sql(q.sql)
    st.caption(f"{len(res):,} row(s) returned")
    if len(res) == 1 and len(res.columns) <= 4:
        cols = st.columns(len(res.columns))
        for col, (name, val) in zip(cols, res.iloc[0].items()):
            col.metric(name.replace("_", " ").title(), f"{val:,}" if pd.api.types.is_number(val) else val)
    else:
        st.dataframe(res.head(1000), width="stretch", hide_index=True)
        if len(res) > 1000:
            st.caption("Preview limited to the first 1,000 rows - download for everything.")
    ui.download_df(res, f"{qid}.csv")


with tab1:
    render(assignment, "sel_q")
with tab2:
    render(advanced, "sel_a")
with tab3:
    st.caption("Read-only connection · single SELECT/WITH statement · capped at 5,000 rows.")
    left, right = st.columns([2, 1])
    with right:
        st.markdown("**Schema · `rides`**")
        schema = db.run_sql("PRAGMA table_info(rides)")[["name", "type"]]
        st.dataframe(schema, hide_index=True, height=420, width="stretch")
        st.caption("Also: `dim_vehicle`, views `v_successful_rides`, `v_cancellations`, `v_daily_kpis`.")
    with left:
        default = ("SELECT Vehicle_Type, Payment_Method, COUNT(*) AS rides,\n"
                   "       ROUND(AVG(Booking_Value), 1) AS avg_value\n"
                   "FROM rides\nWHERE Is_Success = 1\nGROUP BY 1, 2\nORDER BY rides DESC;")
        sql = st.text_area("Your SQL", default, height=220)
        if st.button("▶ Run query", type="primary"):
            try:
                out = db.run_user_sql(sql)
                st.success(f"{len(out):,} rows")
                st.dataframe(out, width="stretch", hide_index=True)
                ui.download_df(out, "custom_query.csv")
            except Exception as e:  # noqa: BLE001 - show any SQL error to the user
                st.error(f"{type(e).__name__}: {e}")
