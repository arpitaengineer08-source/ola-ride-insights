import pytest

from src import analytics as A
from src import db


@pytest.fixture(scope="module")
def rides():
    return A.load_rides()


def test_funnel_is_monotonic(rides):
    f = A.funnel(rides)["rides"].tolist()
    assert f == sorted(f, reverse=True)


def test_kpis_match_sql(rides):
    k = A.kpis(rides)
    assert k["revenue"] == db.run_sql("SELECT SUM(Booking_Value) v FROM rides WHERE Is_Success=1")["v"][0]
    assert round(k["success_rate"], 2) == 62.09


def test_filters_reduce_rows(rides):
    f = A.Filters(rides["Booking_Date"].min(), rides["Booking_Date"].max(), ("Auto",), ("Success",), "Weekend")
    out = A.apply_filters(rides, f)
    assert 0 < len(out) < len(rides)
    assert set(out["Vehicle_Type"].unique()) == {"Auto"} and out["Is_Weekend"].eq(1).all()


def test_insights_never_crash_on_empty(rides):
    assert A.generate_insights(rides.iloc[0:0])[0].tone == "warn"


@pytest.mark.parametrize("bad", [
    "DROP TABLE rides", "DELETE FROM rides", "SELECT 1; DROP TABLE rides",
    "UPDATE rides SET Booking_Value=0", "PRAGMA writable_schema=1",
])
def test_user_sql_is_read_only(bad):
    with pytest.raises(Exception):
        db.run_user_sql(bad)


def test_user_sql_select_ok():
    assert len(db.run_user_sql("SELECT * FROM rides", limit=10)) == 10
