"""
Multi-Lender Student Financing Marketplace -- FastAPI backend.

Run locally with:  uvicorn main:app --reload
Then open http://127.0.0.1:8000/docs for interactive API docs.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
import sqlite3
import time
import os

from matching_engine import Applicant, get_ranked_offers, PARTNERS, CREDIT_TIER_RANK

app = FastAPI(title="Multi-Lender Student Financing Marketplace API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "events.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            event_type TEXT,
            payload TEXT,
            ts REAL
        )"""
    )
    conn.commit()
    conn.close()


init_db()


def log_event(session_id: str, event_type: str, payload: str = ""):
    """Event-level analytics instrumentation -- this is the real
    backing for the 'instrumented event-level analytics to track
    conversion, engagement, and feature adoption' resume claim."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO events (session_id, event_type, payload, ts) VALUES (?, ?, ?, ?)",
        (session_id, event_type, payload, time.time()),
    )
    conn.commit()
    conn.close()


class ApplicantRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session identifier for analytics")
    requested_amount: int = Field(..., gt=0)
    credit_tier: str
    requested_tenure_years: int = Field(..., gt=0, le=30)
    has_cosigner: bool = False


class OfferResponse(BaseModel):
    partner_id: str
    partner_name: str
    eligible: bool
    reason: str
    estimated_rate_pct: Optional[float] = None
    requires_cosigner: bool = False
    max_tenure_years: Optional[int] = None


@app.get("/")
def root():
    return {"service": "Multi-Lender Student Financing Marketplace API", "status": "ok"}


@app.get("/partners")
def list_partners():
    """Stage 1 of the funnel: show the applicant what's on offer before they commit info."""
    return [
        {
            "id": p.id,
            "name": p.name,
            "min_credit_tier": p.min_credit_tier,
            "amount_range": [p.min_amount, p.max_amount],
            "max_tenure_years": p.max_tenure_years,
        }
        for p in PARTNERS
    ]


@app.post("/match", response_model=list[OfferResponse])
def match_offers(req: ApplicantRequest):
    if req.credit_tier not in CREDIT_TIER_RANK:
        raise HTTPException(400, f"credit_tier must be one of {list(CREDIT_TIER_RANK.keys())}")

    log_event(req.session_id, "eligibility_checked", f"amount={req.requested_amount},tier={req.credit_tier}")

    applicant = Applicant(
        requested_amount=req.requested_amount,
        credit_tier=req.credit_tier,
        requested_tenure_years=req.requested_tenure_years,
        has_cosigner=req.has_cosigner,
    )
    offers = get_ranked_offers(applicant)

    log_event(req.session_id, "offers_viewed", f"eligible_count={sum(1 for o in offers if o.eligible)}")

    return [
        OfferResponse(
            partner_id=o.partner_id, partner_name=o.partner_name, eligible=o.eligible,
            reason=o.reason, estimated_rate_pct=o.estimated_rate_pct,
            requires_cosigner=o.requires_cosigner, max_tenure_years=o.max_tenure_years,
        )
        for o in offers
    ]


class SelectionRequest(BaseModel):
    session_id: str
    partner_id: str


@app.post("/select-partner")
def select_partner(req: SelectionRequest):
    """Stage 3 of the funnel: applicant picks an offer."""
    log_event(req.session_id, "partner_selected", req.partner_id)
    return {"status": "recorded", "partner_id": req.partner_id}


@app.post("/initiate-application")
def initiate_application(req: SelectionRequest):
    """Stage 4 of the funnel: applicant starts the actual application."""
    log_event(req.session_id, "application_initiated", req.partner_id)
    return {"status": "application_initiated", "partner_id": req.partner_id}


@app.get("/analytics/funnel")
def funnel_summary():
    """Real, queried-from-the-database funnel conversion -- not invented numbers."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    stages = ["eligibility_checked", "offers_viewed", "partner_selected", "application_initiated"]
    counts = {}
    for stage in stages:
        cur.execute(
            "SELECT COUNT(DISTINCT session_id) FROM events WHERE event_type = ?", (stage,)
        )
        counts[stage] = cur.fetchone()[0]
    conn.close()
    return {"funnel": counts}
