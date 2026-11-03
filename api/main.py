"""FlightGuard API: connection risk from an itinerary."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from api.predictor import predict_connection
from api.schemas import ConnectionRequest, ConnectionResponse

app = FastAPI(
    title="FlightGuard",
    description="Predicts the probability of missing a connecting flight, "
                "using delay forecasts derived from historical US DOT data.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://flightguard-ashen.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Confirm the service is running and the models are loaded."""
    return {"status": "ok"}


@app.post("/predict/connection", response_model=ConnectionResponse)
def predict(request: ConnectionRequest):
    """Assess the risk of missing a single connection."""
    return predict_connection(request.inbound, request.outbound, request.buffer_override)

handler = Mangum(app)