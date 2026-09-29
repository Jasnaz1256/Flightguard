"""Request and response shapes for the API"""

from datetime import date
from pydantic import BaseModel, Field

class Flight(BaseModel):
    """A single flight as it appears on a booking confirmation."""

    carrier: str = Field(..., description="Airline code, e.g. DL", examples=["DL"])
    origin: str = Field(..., description="Departure airport code", examples=["DFW"])
    dest: str = Field(..., description="Arrival airport code", examples=["ATL"])
    fl_date: date = Field(..., description="Date of the flight", examples=["2026-04-14"])
    crs_dep_time: int = Field(..., ge=0, le=2359, description="Scheduled departure, HHMM", examples=[1420])
    crs_arr_time: int = Field(..., ge=0, le=2359, description="Scheduled arrival, HHMM", examples=[1745])

class ConnectionRequest(BaseModel):
    """Two consecutive flights forming a connection."""

    inbound: Flight
    outbound: Flight

    buffer_override: int | None = Field(
        None, ge=0, le=600,
        description="Override the scheduled connection time, in minutes",
    )

class DelayForecast(BaseModel):
    """Predicted delay distribution for one flight, in minutes."""

    p10: float
    p50: float
    p90: float


class ConnectionResponse(BaseModel):
    """Assessment of a single connection."""

    miss_probability: float
    risk_band: str
    scheduled_buffer_minutes: int
    median_time_available: float
    p10_time_available: float
    p90_time_available: float
    inbound_arrival_delay: DelayForecast
    outbound_departure_delay: DelayForecast
    explanation: str