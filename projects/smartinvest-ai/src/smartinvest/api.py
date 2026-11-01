"""FastAPI adapter for the local rule-based detection engine."""
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

from .detection import ENGINE_VERSION, scan_offer
from .batch import screen_csv, MAX_BYTES

app = FastAPI(title="SmartInvest AI research prototype", version=ENGINE_VERSION)


@app.exception_handler(RequestValidationError)
async def validation_error(_request, exc):
    # FastAPI's default errors can include submitted values. Never echo messages,
    # tokens or other user-provided data in validation errors.
    allowed = {"body", "offer_text", "website_url", "claimed_firm", "csv_text"}
    errors = [{"loc": [x if isinstance(x, int) or x in allowed else "unknown_field" for x in error["loc"]],
               "type": error["type"], "msg": error["msg"]} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offer_text: str = Field(default="", max_length=10000)
    website_url: str = Field(default="", max_length=2048)
    claimed_firm: str = Field(default="", max_length=200)


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(max_length=MAX_BYTES)


@app.get("/v1/health")
def health():
    return {"status": "ok"}


@app.post("/v1/scans")
def scan(request: ScanRequest):
    try:
        return scan_offer(
            offer_text=request.offer_text,
            website_url=request.website_url,
            claimed_firm=request.claimed_firm,
        ).as_dict()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/batch-scans")
def batch_scan(request: BatchRequest):
    try:
        return screen_csv(request.csv_text.encode("utf-8"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

from typing import Literal
from .market import analyse_prices

class MarketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    csv_text: str = Field(max_length=MAX_BYTES)
    horizon: Literal[1, 5, 20] = 5

@app.post('/v1/market-research')
def market_research(request: MarketRequest):
    try:
        return analyse_prices(request.csv_text.encode('utf-8'), request.horizon)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
