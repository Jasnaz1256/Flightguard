import { useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const EMPTY_FLIGHT = {
  carrier: "",
  origin: "",
  dest: "",
  fl_date: "",
  crs_dep_time: "",
  crs_arr_time: "",
};

function FlightForm({ label, flight, onChange }) {
  const set = (field) => (e) => onChange({ ...flight, [field]: e.target.value });

  return (
    <fieldset className="flight-form">
      <legend>{label}</legend>
      <div className="grid">
        <label>
          Airline
          <input value={flight.carrier} onChange={set("carrier")} placeholder="DL" maxLength={3} />
        </label>
        <label>
          From
          <input value={flight.origin} onChange={set("origin")} placeholder="DFW" maxLength={4} />
        </label>
        <label>
          To
          <input value={flight.dest} onChange={set("dest")} placeholder="ATL" maxLength={4} />
        </label>
        <label>
          Date
          <input type="date" value={flight.fl_date} onChange={set("fl_date")} />
        </label>
        <label>
          Departs
          <input value={flight.crs_dep_time} onChange={set("crs_dep_time")} placeholder="1420" maxLength={4} />
        </label>
        <label>
          Arrives
          <input value={flight.crs_arr_time} onChange={set("crs_arr_time")} placeholder="1745" maxLength={4} />
        </label>
      </div>
    </fieldset>
  );
}

function Result({ data }) {
  const pct = (data.miss_probability * 100).toFixed(1);

  return (
    <section className="result">
      <div className={`headline band-${data.risk_band.replace(" ", "-")}`}>
        <span className="pct">{pct}%</span>
        <span className="band">{data.risk_band} risk of missing</span>
      </div>

      <p className="explanation">{data.explanation}</p>

      <div className="detail-grid">
        <div>
          <span className="detail-label">Scheduled connection</span>
          <span className="detail-value">{data.scheduled_buffer_minutes} min</span>
        </div>
        <div>
          <span className="detail-label">Typical time at gate</span>
          <span className="detail-value">{Math.round(data.median_time_available)} min</span>
        </div>
        <div>
          <span className="detail-label">Unlucky case (10th pct)</span>
          <span className="detail-value">{Math.round(data.p10_time_available)} min</span>
        </div>
        <div>
          <span className="detail-label">Lucky case (90th pct)</span>
          <span className="detail-value">{Math.round(data.p90_time_available)} min</span>
        </div>
      </div>

      <table className="forecast">
        <thead>
          <tr><th>Predicted delay</th><th>Early case</th><th>Typical</th><th>Late case</th></tr>
        </thead>
        <tbody>
          <tr>
            <td>Inbound arrival</td>
            <td>{data.inbound_arrival_delay.p10} min</td>
            <td>{data.inbound_arrival_delay.p50} min</td>
            <td>{data.inbound_arrival_delay.p90} min</td>
          </tr>
          <tr>
            <td>Outbound departure</td>
            <td>{data.outbound_departure_delay.p10} min</td>
            <td>{data.outbound_departure_delay.p50} min</td>
            <td>{data.outbound_departure_delay.p90} min</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

export default function App() {
  const [inbound, setInbound] = useState({ ...EMPTY_FLIGHT });
  const [outbound, setOutbound] = useState({ ...EMPTY_FLIGHT });
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const toPayload = (f) => ({
    carrier: f.carrier.toUpperCase(),
    origin: f.origin.toUpperCase(),
    dest: f.dest.toUpperCase(),
    fl_date: f.fl_date,
    crs_dep_time: Number(f.crs_dep_time),
    crs_arr_time: Number(f.crs_arr_time),
  });

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch(`${API_URL}/predict/connection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          inbound: toPayload(inbound),
          outbound: toPayload(outbound),
        }),
      });
      if (!response.ok) {
        const detail = await response.json();
        throw new Error(JSON.stringify(detail.detail ?? detail));
      }
      setResult(await response.json());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fillExample = () => {
    setInbound({ carrier: "AA", origin: "LAX", dest: "ORD", fl_date: "2026-04-14", crs_dep_time: "800", crs_arr_time: "1405" });
    setOutbound({ carrier: "AA", origin: "ORD", dest: "BOS", fl_date: "2026-04-14", crs_dep_time: "1440", crs_arr_time: "1755" });
  };

  return (
    <main>
      <header>
        <h1>FlightGuard</h1>
        <p>Connection risk from historical US flight data</p>
      </header>

      <FlightForm label="Inbound flight" flight={inbound} onChange={setInbound} />
      <FlightForm label="Outbound flight" flight={outbound} onChange={setOutbound} />

      <div className="actions">
        <button onClick={submit} disabled={loading}>
          {loading ? "Assessing…" : "Assess connection"}
        </button>
        <button className="secondary" onClick={fillExample}>Use an example</button>
      </div>

      {error && <p className="error">{error}</p>}
      {result && <Result data={result} />}
    </main>
  );
}