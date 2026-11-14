# Business insights - Ola Bengaluru, July 2024

103,024 bookings · 94,544 customers · 7 vehicle types · 50 pickup zones.

## Headline
**Demand is healthy and evenly spread; conversion is the problem.** Only 62.1 % of bookings become rides, and
₹2.15 Cr of the ₹5.65 Cr gross booking value (37.9 %) never materialised.

| Outcome | Rides | Share |
|---|---|---|
| Success | 63,967 | 62.1 % |
| Cancelled by driver | 18,434 | 17.9 % |
| Cancelled by customer | 10,499 | 10.2 % |
| Driver not found | 10,124 | 9.8 % |

## Findings and recommended actions
1. **Driver cancellations are the largest leak** (17.9 %). Top reasons: personal & car issue 35.5 %, customer-related 29.4 %,
   customer sick 19.8 %, over-capacity 15.3 %. → vehicle readiness check, completion incentives, penalties.
2. **Customers cancel when the driver does not approach.** "Driver is not moving towards pickup" (30.2 %) plus
   "Driver asked to cancel" (25.4 %) = 55.7 % of customer cancels. → ETA-drift alerts, auto-reassign, block driver-asked cancels.
3. **Retention is near zero.** 91.6 % of customers booked once; only 498 (0.5 %) booked 3+ times. → second-ride coupons, loyalty.
4. **Cash dominates payments** (54.8 %) vs UPI 40.5 % and cards 4.8 %. → UPI cash-back, driver cash-risk reduction.
5. **Fares are statistically independent of distance** (r = 0.002). Autos average 10 km vs ~25 km elsewhere at the same ~₹550
   fare. → audit the fare field / pricing engine before price decisions.
6. **Vehicle mix is balanced**; Prime Sedan leads on success rate (63.0 %) and realised revenue (₹52.2 L); Prime SUV trails (61.4 %).
7. **No rush hour in the data.** Hourly and weekday demand are almost flat (daily CV ≈ 2 %). Raw Mon-Wed totals are higher only
   because July 2024 has five of each. → target dispatch by failure hot-spots, not by time-of-day.
8. **Failure rate is systemic.** Best vs worst pickup zone differ by ~4 pp (36 % - 40 %), so zone-specific fixes won't move the needle.
9. **Ratings look inflated.** Uniform 3.0-5.0, never below 3, driver/customer ratings uncorrelated. → tag-based feedback.
10. **Incomplete trips:** 3,926 successful bookings (6.1 %) ended incomplete - customer demand 1,601, vehicle breakdown 1,591,
    other 734 - worth ₹22.5 L.

## What-if
Recovering 15 % of driver cancels, 10 % of customer cancels and 10 % of "driver not found" adds ≈ 4,800 rides and ≈ ₹26 L
a month (use the **Impact simulator** page to change the assumptions).

## Caveats
Single month; many distributions are near-uniform and columns largely uncorrelated, which is unusual for real marketplace
data - treat as directional. Booking value on cancelled rides is an *intended* fare, so leakage is an upper bound.
