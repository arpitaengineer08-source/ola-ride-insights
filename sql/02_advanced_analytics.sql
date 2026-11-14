-- =============================================================================
--  OLA RIDE INSIGHTS  |  Part 2 - Advanced analytics (beyond the brief)
--  Window functions, CTEs, conditional aggregation, ranking and anomaly queries.
-- =============================================================================

-- name: a01 | Daily bookings with 7-day moving average
WITH daily AS (
    SELECT Booking_Date, COUNT(*) AS bookings, SUM(Is_Success) AS successful
    FROM   rides GROUP BY Booking_Date
)
SELECT Booking_Date, bookings, successful,
       ROUND(AVG(bookings) OVER (ORDER BY Booking_Date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 1) AS bookings_ma7
FROM   daily
ORDER  BY Booking_Date;

-- name: a02 | Demand heat-map - bookings per weekday and hour
SELECT Day_Of_Week, Day_Name, Booking_Hour, COUNT(*) AS bookings
FROM   rides
GROUP  BY Day_Of_Week, Day_Name, Booking_Hour
ORDER  BY Day_Of_Week, Booking_Hour;

-- name: a03 | Weekday demand normalised per calendar day (July 2024 has 5 Mon/Tue/Wed)
WITH per_day AS (
    SELECT Booking_Date, Day_Of_Week, Day_Name, COUNT(*) AS bookings
    FROM   rides GROUP BY Booking_Date, Day_Of_Week, Day_Name
)
SELECT Day_Name, COUNT(*) AS days_in_month, SUM(bookings) AS total_bookings,
       ROUND(AVG(bookings), 1) AS avg_bookings_per_day
FROM   per_day
GROUP  BY Day_Of_Week, Day_Name
ORDER  BY Day_Of_Week;

-- name: a04 | Revenue leakage - booking value lost to non-successful bookings
SELECT Vehicle_Type,
       SUM(CASE WHEN Is_Success = 1 THEN Booking_Value ELSE 0 END)                       AS realised_value,
       SUM(CASE WHEN Is_Success = 0 THEN Booking_Value ELSE 0 END)                       AS leaked_value,
       ROUND(100.0 * SUM(CASE WHEN Is_Success = 0 THEN Booking_Value ELSE 0 END)
                   / SUM(Booking_Value), 2)                                              AS leakage_pct
FROM   rides
GROUP  BY Vehicle_Type
ORDER  BY leaked_value DESC;

-- name: a05 | Cancellation reasons ranked within each party (customer vs driver)
SELECT Cancel_Party, Cancel_Reason, COUNT(*) AS cancellations,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY Cancel_Party), 1) AS pct_within_party,
       RANK() OVER (PARTITION BY Cancel_Party ORDER BY COUNT(*) DESC)               AS reason_rank
FROM   rides
WHERE  Cancel_Reason IS NOT NULL
GROUP  BY Cancel_Party, Cancel_Reason
ORDER  BY Cancel_Party, reason_rank;

-- name: a06 | Pickup hotspots with the highest failure rate (min 1,500 bookings)
SELECT Pickup_Location,
       COUNT(*)                                       AS bookings,
       ROUND(100.0 * (1 - AVG(Is_Success)), 2)        AS failure_rate_pct,
       SUM(CASE WHEN Booking_Status = 'Driver Not Found' THEN 1 ELSE 0 END) AS driver_not_found
FROM   rides
GROUP  BY Pickup_Location
HAVING COUNT(*) >= 1500
ORDER  BY failure_rate_pct DESC
LIMIT  10;

-- name: a07 | Top 10 busiest routes (pickup -> drop, excluding same-location trips)
SELECT Pickup_Location || ' -> ' || Drop_Location AS route,
       COUNT(*) AS bookings, SUM(Is_Success) AS successful,
       ROUND(AVG(CASE WHEN Is_Success = 1 THEN Booking_Value END), 0) AS avg_fare
FROM   rides
WHERE  Pickup_Location <> Drop_Location
GROUP  BY Pickup_Location, Drop_Location
ORDER  BY bookings DESC
LIMIT  10;

-- name: a08 | Customer loyalty segments (one-time / occasional / frequent)
WITH per_customer AS (
    SELECT Customer_ID, COUNT(*) AS rides, SUM(Is_Success) AS successful, SUM(Booking_Value) AS value
    FROM   rides GROUP BY Customer_ID
)
SELECT CASE WHEN rides = 1 THEN '1 - One-time'
            WHEN rides = 2 THEN '2 - Occasional (2 rides)'
            ELSE '3 - Frequent (3+ rides)' END AS segment,
       COUNT(*)                                  AS customers,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_customers,
       SUM(value)                                AS booking_value
FROM   per_customer
GROUP  BY segment
ORDER  BY segment;

-- name: a09 | Serial cancellers - customers who cancelled 2+ times
SELECT Customer_ID, COUNT(*) AS customer_cancellations, SUM(Booking_Value) AS blocked_value
FROM   rides
WHERE  Booking_Status = 'Canceled by Customer'
GROUP  BY Customer_ID
HAVING COUNT(*) >= 2
ORDER  BY customer_cancellations DESC, blocked_value DESC
LIMIT  20;

-- name: a10 | Payment mix by vehicle type (successful rides)
SELECT Vehicle_Type, Payment_Method, COUNT(*) AS rides,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY Vehicle_Type), 1) AS pct_of_vehicle
FROM   rides
WHERE  Is_Success = 1
GROUP  BY Vehicle_Type, Payment_Method
ORDER  BY Vehicle_Type, rides DESC;

-- name: a11 | Driver vs customer rating gap by vehicle type
SELECT Vehicle_Type,
       ROUND(AVG(Driver_Ratings), 3)                         AS avg_driver_rating,
       ROUND(AVG(Customer_Rating), 3)                        AS avg_customer_rating,
       ROUND(AVG(Driver_Ratings) - AVG(Customer_Rating), 3)  AS gap,
       SUM(CASE WHEN Driver_Ratings < 3.5 THEN 1 ELSE 0 END) AS low_driver_ratings
FROM   rides
WHERE  Is_Success = 1
GROUP  BY Vehicle_Type
ORDER  BY gap DESC;

-- name: a12 | Anomaly watch-list - flagged successful rides, highest fare per km
SELECT Booking_ID, Booking_Date, Customer_ID, Vehicle_Type, Pickup_Location, Drop_Location,
       Ride_Distance, Booking_Value, Fare_Per_Km, Flag_Same_Pickup_Drop, Flag_Fare_Outlier
FROM   rides
WHERE  Flag_Same_Pickup_Drop = 1 OR Flag_Fare_Outlier = 1
ORDER  BY Fare_Per_Km DESC
LIMIT  50;

-- name: a13 | Turnaround time (TAT) benchmarks by time band
SELECT Time_Band,
       COUNT(*)                                  AS rides,
       ROUND(AVG(V_TAT), 1)                      AS avg_vehicle_tat,
       ROUND(AVG(C_TAT), 1)                      AS avg_customer_tat,
       ROUND(AVG(Booking_Value), 1)              AS avg_fare
FROM   rides
WHERE  Is_Success = 1
GROUP  BY Time_Band
ORDER  BY CASE Time_Band WHEN 'Morning' THEN 1 WHEN 'Afternoon' THEN 2 WHEN 'Evening' THEN 3 ELSE 4 END;

-- name: a14 | Cumulative revenue curve (running total with window function)
WITH d AS (
    SELECT Booking_Date, SUM(CASE WHEN Is_Success = 1 THEN Booking_Value ELSE 0 END) AS revenue
    FROM rides GROUP BY Booking_Date
)
SELECT Booking_Date, revenue,
       SUM(revenue) OVER (ORDER BY Booking_Date) AS cumulative_revenue
FROM   d
ORDER  BY Booking_Date;
