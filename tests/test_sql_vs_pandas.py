"""Validate every brief question: SQLite answer == pandas answer computed from the raw Excel."""
import pandas as pd
import pytest

from src import db


def sql(qid: str) -> pd.DataFrame:
    return db.run_sql(db.all_queries()[qid].sql)


def test_row_count(raw):
    assert db.run_sql("SELECT COUNT(*) n FROM rides")["n"][0] == len(raw) == 103_024


def test_q01_successful_bookings(raw):
    assert len(sql("q01")) == (raw["Booking_Status"] == "Success").sum()


def test_q02_avg_distance(raw):
    r = sql("q02").set_index("Vehicle_Type")
    raw = raw.assign(Vehicle_Type=raw["Vehicle_Type"].replace({"eBike": "E-Bike"}))
    exp_all = raw.groupby("Vehicle_Type")["Ride_Distance"].mean().round(2)
    exp_ok = raw[raw["Booking_Status"] == "Success"].groupby("Vehicle_Type")["Ride_Distance"].mean().round(2)
    pd.testing.assert_series_equal(r["avg_km_all_bookings"].sort_index(), exp_all.sort_index(), check_names=False)
    pd.testing.assert_series_equal(r["avg_km_successful_only"].sort_index(), exp_ok.sort_index(), check_names=False)


def test_q03_customer_cancellations(raw):
    assert sql("q03").iloc[0, 0] == (raw["Booking_Status"] == "Canceled by Customer").sum() == 10_499


def test_q04_top5_customers(raw):
    r = sql("q04")
    counts = raw["Customer_ID"].value_counts()
    assert r["total_rides"].tolist() == sorted(counts.head(5).tolist(), reverse=True)
    assert r.loc[0, "Customer_ID"] == counts.index[0]          # the only 5-ride customer


def test_q05_driver_personal_car(raw):
    assert sql("q05").iloc[0, 0] == (raw["Canceled_Rides_by_Driver"] == "Personal & Car related issue").sum() == 6_542


def test_q06_prime_sedan_ratings(raw):
    ps = raw[raw["Vehicle_Type"] == "Prime Sedan"]["Driver_Ratings"]
    r = sql("q06").iloc[0]
    assert (r["max_driver_rating"], r["min_driver_rating"]) == (ps.max(), ps.min())


def test_q07_upi(raw):
    assert len(sql("q07")) == (raw["Payment_Method"] == "UPI").sum()


def test_q08_avg_customer_rating(raw):
    exp = raw.assign(Vehicle_Type=raw["Vehicle_Type"].replace({"eBike": "E-Bike"})).groupby("Vehicle_Type")["Customer_Rating"].mean().round(3)
    got = sql("q08").set_index("Vehicle_Type")["avg_customer_rating"]
    pd.testing.assert_series_equal(got.sort_index(), exp.sort_index(), check_names=False)


def test_q09_total_value(raw):
    r = sql("q09").iloc[0]
    ok = raw[raw["Booking_Status"] == "Success"]
    assert r["value_all_success"] == ok["Booking_Value"].sum() == 35_080_467
    assert r["value_strictly_completed"] == ok[ok["Incomplete_Rides"] == "No"]["Booking_Value"].sum()
    assert r["value_all_success"] == r["value_strictly_completed"] + r["value_success_but_incomplete"]


def test_q10_incomplete_rides(raw):
    r = sql("q10")
    exp = raw[raw["Incomplete_Rides"] == "Yes"]
    assert len(r) == len(exp) == 3_926
    assert r["Incomplete_Rides_Reason"].value_counts().to_dict() == exp["Incomplete_Rides_Reason"].value_counts().to_dict()


@pytest.mark.parametrize("qid", [q for q in db.all_queries()])
def test_every_query_executes(qid):
    assert isinstance(sql(qid), pd.DataFrame)


def test_advanced_consistency(raw):
    # leakage + realised == gross
    a4 = sql("a04")
    assert (a4["realised_value"] + a4["leaked_value"]).sum() == raw["Booking_Value"].sum()
    # loyalty segments partition all customers
    assert sql("a08")["customers"].sum() == raw["Customer_ID"].nunique()
    # cumulative revenue ends at total realised revenue
    assert sql("a14")["cumulative_revenue"].iloc[-1] == 35_080_467
