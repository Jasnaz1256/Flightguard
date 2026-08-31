TRUNCATE connections;

INSERT INTO connections (inbound_flight_id, outbound_flight_id, airport, buffer_minutes, missed_connection)
SELECT
    inb.flight_id,
    outb.flight_id,
    inb.dest,
    ((outb.crs_dep_time / 100) * 60 + outb.crs_dep_time % 100)
      - ((inb.crs_arr_time / 100) * 60 + inb.crs_arr_time % 100) AS buffer_minutes,
    CASE WHEN inb.arr_delay + 15 >
        --((outb.crs_dep_time / 100) * 60 + outb.crs_dep_time % 100)
        ((outb.dep_time / 100) * 60 + outb.dep_time % 100)
        - ((inb.crs_arr_time / 100) * 60 + inb.crs_arr_time % 100)
    THEN 1 ELSE 0 END AS missed_connection
FROM flights inb
JOIN flights outb
  ON  inb.dest = outb.origin
  AND inb.fl_date = outb.fl_date
  AND inb.carrier = outb.carrier
  AND inb.flight_id <> outb.flight_id
  AND inb.origin <> outb.dest
  AND random() < 0.15
  AND ((outb.crs_dep_time / 100) * 60 + outb.crs_dep_time % 100)
      - ((inb.crs_arr_time / 100) * 60 + inb.crs_arr_time % 100)
      BETWEEN 30 AND 180;