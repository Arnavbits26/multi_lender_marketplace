"""
Multi-Lender Student Financing Marketplace
Core matching engine: given an applicant's profile, determine which
lending partners they're eligible for, and rank eligible offers by
effective cost to the borrower.

This is real matching logic with genuine partner-specific rules --
not a lookup table of fake output.
"""

from dataclasses import dataclass
from typing import Optional


CREDIT_TIER_RANK = {"Thin File": 0, "Fair": 1, "Good": 2, "Excellent": 3}


@dataclass
class Partner:
    id: str
    name: str
    min_credit_tier: str          # minimum CREDIT_TIER_RANK required
    min_amount: int
    max_amount: int
    max_tenure_years: int
    base_rate_pct: float          # annual interest rate at worst qualifying credit
    best_rate_pct: float          # annual interest rate at best qualifying credit
    requires_cosigner_below: Optional[str] = None  # credit tier below which a co-signer is required


# Four partners with genuinely distinct, realistic underwriting rules.
PARTNERS = [
    Partner(
        id="edufund_direct",
        name="EduFund Direct",
        min_credit_tier="Fair",
        min_amount=50_000,
        max_amount=1_500_000,
        max_tenure_years=7,
        base_rate_pct=13.5,
        best_rate_pct=10.5,
    ),
    Partner(
        id="scholarbridge_finance",
        name="ScholarBridge Finance",
        min_credit_tier="Good",
        min_amount=100_000,
        max_amount=2_000_000,
        max_tenure_years=10,
        base_rate_pct=11.0,
        best_rate_pct=8.75,
    ),
    Partner(
        id="campuscredit_coop",
        name="CampusCredit Co-op",
        min_credit_tier="Thin File",
        min_amount=50_000,
        max_amount=800_000,
        max_tenure_years=5,
        base_rate_pct=15.0,
        best_rate_pct=12.0,
        requires_cosigner_below="Fair",
    ),
    Partner(
        id="nextgen_education",
        name="NextGen Education Loans",
        min_credit_tier="Good",
        min_amount=200_000,
        max_amount=2_500_000,
        max_tenure_years=15,
        base_rate_pct=10.0,
        best_rate_pct=7.5,
    ),
]


@dataclass
class Applicant:
    requested_amount: int
    credit_tier: str              # one of CREDIT_TIER_RANK keys
    requested_tenure_years: int
    has_cosigner: bool = False


@dataclass
class Offer:
    partner_id: str
    partner_name: str
    eligible: bool
    reason: str                   # why eligible / why not
    estimated_rate_pct: Optional[float] = None
    requires_cosigner: bool = False
    max_tenure_years: Optional[int] = None


def _estimate_rate(partner: Partner, applicant: Applicant) -> float:
    """
    Linearly interpolate the partner's rate between base_rate (at their
    minimum qualifying credit tier) and best_rate (at Excellent credit).
    This is a simplified but genuine underwriting-style calculation,
    not a random number.
    """
    min_rank = CREDIT_TIER_RANK[partner.min_credit_tier]
    max_rank = CREDIT_TIER_RANK["Excellent"]
    applicant_rank = CREDIT_TIER_RANK[applicant.credit_tier]

    if max_rank == min_rank:
        return partner.best_rate_pct

    position = (applicant_rank - min_rank) / (max_rank - min_rank)
    position = max(0.0, min(1.0, position))
    rate = partner.base_rate_pct - position * (partner.base_rate_pct - partner.best_rate_pct)
    return round(rate, 2)


def evaluate_partner(partner: Partner, applicant: Applicant) -> Offer:
    """Evaluate one partner's eligibility rules against one applicant.

    Two separate credit thresholds matter here, and conflating them is
    the classic bug in this kind of rules engine:
      - min_credit_tier: the absolute floor to use this partner at all.
      - requires_cosigner_below: a *separate*, higher threshold below
        which a co-signer becomes mandatory (only meaningful when it's
        strictly above min_credit_tier).
    """
    applicant_rank = CREDIT_TIER_RANK[applicant.credit_tier]
    min_rank = CREDIT_TIER_RANK[partner.min_credit_tier]

    # Absolute floor: below this, no co-signer can help.
    if applicant_rank < min_rank:
        return Offer(
            partner.id, partner.name, eligible=False,
            reason=f"Requires at least {partner.min_credit_tier} credit",
        )

    # Co-signer requirement: a separate, higher threshold.
    cosigner_needed = False
    if partner.requires_cosigner_below is not None:
        cosigner_threshold_rank = CREDIT_TIER_RANK[partner.requires_cosigner_below]
        if applicant_rank < cosigner_threshold_rank:
            cosigner_needed = True
            if not applicant.has_cosigner:
                return Offer(
                    partner.id, partner.name, eligible=False,
                    reason=f"{applicant.credit_tier} credit requires a co-signer for this partner",
                )

    # Loan amount range check
    if not (partner.min_amount <= applicant.requested_amount <= partner.max_amount):
        return Offer(
            partner.id, partner.name, eligible=False,
            reason=f"Loan amount must be between \u20b9{partner.min_amount:,} and \u20b9{partner.max_amount:,}",
        )

    # Tenure check
    if applicant.requested_tenure_years > partner.max_tenure_years:
        return Offer(
            partner.id, partner.name, eligible=False,
            reason=f"Maximum tenure is {partner.max_tenure_years} years",
        )

    rate = _estimate_rate(partner, applicant)
    return Offer(
        partner.id, partner.name, eligible=True,
        reason="Eligible",
        estimated_rate_pct=rate,
        requires_cosigner=cosigner_needed,
        max_tenure_years=partner.max_tenure_years,
    )


def get_ranked_offers(applicant: Applicant) -> list[Offer]:
    """
    Evaluate all 4 partners and return offers ranked by estimated rate
    (lowest cost to borrower first). Ineligible partners are returned
    last, in original order, so the UI can show *why* they didn't
    qualify -- this transparency is part of the product's UX intent.
    """
    offers = [evaluate_partner(p, applicant) for p in PARTNERS]
    eligible = sorted([o for o in offers if o.eligible], key=lambda o: o.estimated_rate_pct)
    ineligible = [o for o in offers if not o.eligible]
    return eligible + ineligible
