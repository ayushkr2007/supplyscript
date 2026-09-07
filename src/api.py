"""
SupplyPrescript - Mid-Review: Write-Back Architecture
--------------------------------------------------------------------------
FastAPI backend that lets the dashboard "Execute Decision" button
persist a chosen prescription back into an operational database
(SQLite locally -- a lightweight stand-in for the Snowflake write-back
described in the project stack; same pattern, easier to run for
local development and grading).

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
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DB_PATH = "data/supplyprescript.db"
PRESCRIPTIONS_PATH = "data/prescriptions.json"

app = FastAPI(title="SupplyPrescript Write-Back API")

# Allow the local Vite dev server (dashboard) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    Path("data").mkdir(exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            decision TEXT NOT NULL,
            cost REAL NOT NULL,
            expected_loss_before REAL NOT NULL,
            expected_loss_after REAL NOT NULL,
            risk_score REAL NOT NULL,
            executed_at TEXT NOT NULL,
            actual_outcome TEXT,
            actual_cost REAL
        )
    """)
    conn.commit()
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
    executed_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO decisions
           (order_id, decision, cost, expected_loss_before,
            expected_loss_after, risk_score, executed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (decision.order_id, decision.decision, decision.cost,
         decision.expected_loss_before, decision.expected_loss_after,
         decision.risk_score, executed_at),
    )
    conn.commit()
    new_id = cur.lastrowid
    row = conn.execute("SELECT * FROM decisions WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)


@app.get("/decisions", response_model=list[DecisionOut])
def list_decisions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM decisions ORDER BY executed_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/decisions/{decision_id}", response_model=DecisionOut)
def get_decision(decision_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return dict(row)


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
    return {"status": "SupplyPrescript API running", "docs": "/docs"}
