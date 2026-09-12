DROP TABLE IF EXISTS flight_rotations;

CREATE TABLE flight_rotations AS
SELECT
    flight_id,
    tail_num,
    fl_date,
    ROW_NUMBER() OVER (PARTITION BY tail_num, fl_date ORDER BY crs_dep_time)
    AS leg_number,
    LAG(crs_arr_time) OVER (PARTITION BY tail_num, fl_date ORDER BY crs_dep_time)
    AS prev_crs_arr_time,
    LAG(arr_delay) OVER (PARTITION BY tail_num, fl_date ORDER BY crs_dep_time)
    AS prev_arr_delay

FROM flights
WHERE tail_num IS NOT NULL;
