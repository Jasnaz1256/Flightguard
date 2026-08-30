INSERT INTO flights(
    fl_date, carrier, origin, dest, crs_dep_time, crs_arr_time, dep_time, arr_time,
    dep_delay, arr_delay, cancelled, tail_num, flight_num
)
SELECT
    fl_date_raw::DATE,
    carrier,
    origin,
    dest,
    NULLIF(crs_dep_time, '')::INT,
    NULLIF(crs_arr_time, '')::INT,
    NULLIF(dep_time, '')::INT,
    NULLIF(arr_time, '')::INT,
    NULLIF(dep_delay_minutes, '')::FLOAT,
    NULLIF(arr_delay_minutes, '')::FLOAT,
    cancelled::NUMERIC::INT,
    tail_num,
    flight_num
FROM flights_staging
WHERE cancelled::NUMERIC::INT = 0
AND arr_delay_minutes <> '';
