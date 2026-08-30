DROP TABLE IF EXISTS connections;
DROP TABLE IF EXISTS flights;

CREATE TABLE flights (
    flight_id    SERIAL PRIMARY KEY,
    fl_date      DATE NOT NULL,
    carrier      VARCHAR(10),
    origin       VARCHAR(5),
    dest         VARCHAR(5), 
    crs_dep_time INT,
    crs_arr_time INT,
    dep_time      INT,
    arr_time      INT,
    dep_delay     INT,
    arr_delay     INT,
    cancelled     SMALLINT DEFAULT 0,
    tail_num     VARCHAR(20),
    flight_num   VARCHAR(10)

);

CREATE INDEX idx_flights_dest_date ON flights (dest, fl_date);
CREATE INDEX idx_flights_origin_date ON flights (origin, fl_date);

CREATE TABLE connections (
    connection_id SERIAL PRIMARY KEY,
    inbound_flight_id INT REFERENCES flights(flight_id),
    outbound_flight_id INT REFERENCES flights(flight_id),
    airport VARCHAR(5),
    buffer_minutes INT,
    missed_connection SMALLINT,
    created_at TIMESTAMP DEFAULT NOW()
);