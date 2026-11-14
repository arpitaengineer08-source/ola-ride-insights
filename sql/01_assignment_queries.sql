-- =============================================================================
--  OLA RIDE INSIGHTS  |  Part 1 - The 10 mandatory SQL questions
--  Engine : SQLite 3 (also runs on MySQL 8 / PostgreSQL - see docs/SQL_NOTES.md)
--  Table  : rides   (cleaned fact table produced by `python -m src.etl`)
--  Format : each block starts with  "-- name: <id> | <title>"  so the Streamlit
--           app can discover and run every query automatically.
-- =============================================================================

-- name: q01 | Retrieve all successful bookings
-- note: 63,967 rows. The app shows a preview; run it in full from a SQL client if needed.
SELECT Booking_ID, Booking_Date, Booking_Time, Customer_ID, Vehicle_Type,
       Pickup_Location, Drop_Location, Ride_Distance, Booking_Value,
       Payment_Method, Driver_Ratings, Customer_Rating
FROM   rides
WHERE  Booking_Status = 'Success'
ORDER  BY Booking_Timestamp;

-- name: q02 | Average ride distance for each vehicle type
-- note: Two lenses. "all_bookings" reproduces the reference sheet in the dataset (zeros from
--       cancelled rides drag it down); "successful_only" is the true average trip length.
SELECT Vehicle_Type,
       ROUND(AVG(Ride_Distance), 2)                                            AS avg_km_all_bookings,
       ROUND(AVG(CASE WHEN Is_Success = 1 THEN Ride_Distance END), 2)          AS avg_km_successful_only
FROM   rides
GROUP  BY Vehicle_Type
ORDER  BY avg_km_successful_only DESC;

-- name: q03 | Total number of rides cancelled by customers
SELECT COUNT(*) AS cancelled_by_customer
FROM   rides
WHERE  Booking_Status = 'Canceled by Customer';

-- name: q04 | Top 5 customers by number of rides
-- note: Many customers tie on 4 rides, so total booking value is used as a deterministic tie-breaker.
SELECT Customer_ID,
       COUNT(*)           AS total_rides,
       SUM(Booking_Value) AS total_booking_value
FROM   rides
GROUP  BY Customer_ID
ORDER  BY total_rides DESC, total_booking_value DESC
LIMIT  5;

-- name: q05 | Rides cancelled by drivers for personal and car-related issues
SELECT COUNT(*) AS driver_cancellations_personal_car
FROM   rides
WHERE  Canceled_Rides_by_Driver = 'Personal & Car related issue';

-- name: q06 | Maximum and minimum driver ratings for Prime Sedan bookings
SELECT MAX(Driver_Ratings) AS max_driver_rating,
       MIN(Driver_Ratings) AS min_driver_rating,
       COUNT(Driver_Ratings) AS rated_rides
FROM   rides
WHERE  Vehicle_Type = 'Prime Sedan';

-- name: q07 | All rides where payment was made using UPI
SELECT Booking_ID, Booking_Date, Customer_ID, Vehicle_Type, Booking_Value, Ride_Distance
FROM   rides
WHERE  Payment_Method = 'UPI'
ORDER  BY Booking_Timestamp;

-- name: q08 | Average customer rating per vehicle type
SELECT Vehicle_Type,
       ROUND(AVG(Customer_Rating), 3) AS avg_customer_rating,
       COUNT(Customer_Rating)         AS rated_rides
FROM   rides
GROUP  BY Vehicle_Type
ORDER  BY avg_customer_rating DESC;

-- name: q09 | Total booking value of successfully completed rides
-- note: "Success" status = 63,967 rides. Strictly finished trips (Incomplete_Rides = 'No') are shown alongside.
SELECT SUM(CASE WHEN Booking_Status = 'Success' THEN Booking_Value END)                              AS value_all_success,
       SUM(CASE WHEN Booking_Status = 'Success' AND Incomplete_Rides = 'No' THEN Booking_Value END)   AS value_strictly_completed,
       SUM(CASE WHEN Incomplete_Rides = 'Yes' THEN Booking_Value END)                                 AS value_success_but_incomplete
FROM   rides;

-- name: q10 | All incomplete rides along with the reason
SELECT Booking_ID, Booking_Date, Vehicle_Type, Pickup_Location, Drop_Location,
       Booking_Value, Incomplete_Rides_Reason
FROM   rides
WHERE  Incomplete_Rides = 'Yes'
ORDER  BY Incomplete_Rides_Reason, Booking_Timestamp;
