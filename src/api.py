"""
SupplyPrescript - Week 4, Day 2: Snowflake Write-Back
--------------------------------------------------------------------------
Replaces the local SQLite write-back (used from Mid-Review through Week 3
for easy local development) with the Snowflake write-back the original
project stack specified. SQLite worked fine on one machine, but a
deployed backend (Week 4 Day 3+) has no persistent local disk -- the
decisions table needs to live somewhere that survives a redeploy and is
reachable from wherever the backend actually runs.

Endpoints are unchanged from the Mid-Review API -- same request/response
shapes, same dashboard contract. Only the storage layer changed.

Credentials are read from environment variables (see .env.example),
never committed. Locally, put a real .env file (already gitignored) in
the repo root; in production, set the same variables in your hosting
platform's environment settings.

Endpoints:
  POST /decisions       -- insert an executed decision
  GET  /decisions        -- list all executed decisions (feeds Week 3's
                             Feedback UI / Decision ROI view)
  GET  /decisions/{id}   -- fetch one decision
  GET  /prescriptions    -- serve the current batch of prescriptions
                             (reads data/prescriptions.json)

Run with:
    uvicorn src.api:app --reload --port 8000
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import snowflake.connector
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# Lets us keep the same "?" placeholder style the SQLite version used,
# instead of Snowflake's default %(name)s pyformat placeholders.
snowflake.connector.paramstyle = "qmark"

PRESCRIPTIONS_PATH = "data/prescriptions.json"

SNOWFLAKE_CONFIG = {
    "account": os.environ["SNOWFLAKE_ACCOUNT"],
    "user": os.environ["SNOWFLAKE_USER"],
    "password": os.environ["SNOWFLAKE_PASSWORD"],
    "warehouse": os.environ.get("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
    "database": os.environ.get("SNOWFLAKE_DATABASE", "SUPPLYPRESCRIPT"),
    "schema": os.environ.get("SNOWFLAKE_SCHEMA", "PUBLIC"),
}

# CORS origins the deployed dashboard will actually call from -- Day 4
# adds the real Vercel URL here once it exists.
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
if extra_origin := os.environ.get("DASHBOARD_ORIGIN"):
    ALLOWED_ORIGINS.append(extra_origin)

app = FastAPI(title="SupplyPrescript Write-Back API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    return snowflake.connector.connect(**SNOWFLAKE_CONFIG)


def row_to_dict(row: dict) -> dict:
    """Snowflake returns unquoted column names in upper case; the
    Pydantic models below use lower_snake_case field names to match
    the original SQLite API contract exactly, so normalize here."""
    return {k.lower(): v for k, v in row.items()}


def init_db():
    conn = get_db()
    try:
        conn.cursor().execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER AUTOINCREMENT PRIMARY KEY,
                order_id INTEGER NOT NULL,
                decision STRING NOT NULL,
                cost FLOAT NOT NULL,
                expected_loss_before FLOAT NOT NULL,
                expected_loss_after FLOAT NOT NULL,
                risk_score FLOAT NOT NULL,
                executed_at STRING NOT NULL,
                actual_outcome STRING,
                actual_cost FLOAT
            )
        """)
    finally:
        conn.close()


class DecisionIn(BaseModel):
    order_id: int
    decision: str
    cost: float
    expected_loss_before: float
    expected_loss_after: float
    risk_score: float


class DecisionOut(DecisionIn):
    id: int
    executed_at: str
    actual_outcome: Optional[str] = None
    actual_cost: Optional[float] = None


@app.on_event("startup")
def on_startup():
    init_db()


@app.post("/decisions", response_model=DecisionOut)
def create_decision(decision: DecisionIn):
    if decision.decision not in ("upgrade", "discount", "nothing"):
        raise HTTPException(status_code=400, detail="Invalid decision type")

    conn = get_db()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        # executed_at carries microsecond precision, so pairing it with
        # order_id is unique enough to look the new row back up --
        # Snowflake's connector doesn't expose a SQLite-style lastrowid.
        executed_at = datetime.now(timezone.utc).isoformat()
        cur.execute(
            """INSERT INTO decisions
               (order_id, decision, cost, expected_loss_before,
                expected_loss_after, risk_score, executed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (decision.order_id, decision.decision, decision.cost,
             decision.expected_loss_before, decision.expected_loss_after,
             decision.risk_score, executed_at),
        )
        cur.execute(
            "SELECT * FROM decisions WHERE order_id = ? AND executed_at = ?",
            (decision.order_id, executed_at),
        )
        row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=500, detail="Insert succeeded but could not read the row back")
    return row_to_dict(row)


@app.get("/decisions", response_model=list[DecisionOut])
def list_decisions():
    conn = get_db()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute("SELECT * FROM decisions ORDER BY executed_at DESC")
        rows = cur.fetchall()
    finally:
        conn.close()
    return [row_to_dict(r) for r in rows]


@app.get("/decisions/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: int):
    conn = get_db()
    try:
        cur = conn.cursor(snowflake.connector.DictCursor)
        cur.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
        row = cur.fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return row_to_dict(row)


@app.get("/prescriptions")
def get_prescriptions():
    path = Path(PRESCRIPTIONS_PATH)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail="No prescriptions found. Run src/w2_day3_json_output.py first.",
        )
    with open(path) as f:
        return json.load(f)


@app.get("/")
def root():
    return {"status": "SupplyPrescript API running (Snowflake write-back)", "docs": "/docs"}
