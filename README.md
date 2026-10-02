# Multi-Lender Student Financing Marketplace

A product case study: a matching engine that evaluates a student loan
applicant against four lending partners' distinct underwriting rules,
ranks eligible offers by estimated rate, and instruments the full
user journey as analytics events.

**[Live interactive demo →](https://claude.ai/artifact/FsdkyGC1yEBf9bebVtmXRP)**

## What this actually is

This started as a resume bullet describing a product case study. It's
now a real, tested matching engine with a working API behind it —
not just a PRD and a mockup.

- **`prd/PRD.pdf`** — the actual product requirements document: problem
  statement, personas, user stories, functional requirements, KPIs,
  MVP scope, and roadmap.
- **`backend/matching_engine.py`** — the real eligibility and
  rate-ranking logic for 4 partners with genuinely distinct rules
  (different minimum credit tiers, loan amount ranges, tenure caps,
  and a co-signer condition for one partner).
- **`backend/tests/test_matching_engine.py`** — 7 passing unit tests,
  including a regression test for a real bug caught during development
  (see below).
- **`backend/main.py`** — a FastAPI backend exposing `/match`,
  `/partners`, `/select-partner`, `/initiate-application`, and a
  `/analytics/funnel` endpoint that returns genuine, queried
  conversion counts from a SQLite event log — not invented numbers.
- **`demo/index.html`** — a self-contained interactive demo that
  mirrors the Python matching logic in JavaScript, so anyone can try
  it without running the backend locally.

## A real bug, caught and fixed

Early in development, a Thin File applicant *without* a co-signer was
incorrectly shown as eligible for CampusCredit Co-op — a partner that
requires a co-signer below Fair credit. The bug: eligibility had only
one credit-tier field (`min_credit_tier`), conflating "minimum tier to
use this partner at all" with "minimum tier to use it *without* a
co-signer." These are different thresholds. The fix separates them
into `min_credit_tier` (absolute floor) and `requires_cosigner_below`
(a distinct, higher threshold). `test_thin_file_without_cosigner_is_fully_ineligible`
is the regression test that would catch this again.

## Run it yourself

```bash
cd backend
pip install fastapi uvicorn pydantic pytest
python -m pytest tests/ -v          # run the test suite
uvicorn main:app --reload           # start the API at localhost:8000/docs
```

## Partner rules modelled

| Partner | Min. Credit | Amount Range | Max Tenure | Rate Range |
|---|---|---|---|---|
| EduFund Direct | Fair | ₹50K – ₹15L | 7 yrs | 10.5–13.5% |
| ScholarBridge Finance | Good | ₹1L – ₹20L | 10 yrs | 8.75–11.0% |
| CampusCredit Co-op | Thin File* | ₹50K – ₹8L | 5 yrs | 12.0–15.0% |
| NextGen Education Loans | Good | ₹2L – ₹25L | 15 yrs | 7.5–10.0% |

\*Thin File accepted only with a co-signer.

## Repository structure

```
multi_lender_marketplace/
├── prd/
│   ├── PRD.tex
│   └── PRD.pdf
├── backend/
│   ├── matching_engine.py
│   ├── main.py
│   └── tests/
│       └── test_matching_engine.py
├── demo/
│   └── index.html
└── README.md
```

## Tech stack

Python, FastAPI, Pydantic, SQLite (event logging), pytest, and a
vanilla HTML/JS interactive demo.
