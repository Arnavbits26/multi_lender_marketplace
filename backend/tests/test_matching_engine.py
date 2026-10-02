import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from matching_engine import Applicant, get_ranked_offers, evaluate_partner, PARTNERS


def offer_for(partner_id, offers):
    return next(o for o in offers if o.partner_id == partner_id)


def test_thin_file_without_cosigner_is_fully_ineligible():
    app = Applicant(requested_amount=300_000, credit_tier="Thin File", requested_tenure_years=4, has_cosigner=False)
    offers = get_ranked_offers(app)
    assert all(not o.eligible for o in offers), "Thin File with no co-signer should qualify for zero partners"


def test_thin_file_with_cosigner_qualifies_for_campuscredit_only():
    app = Applicant(requested_amount=300_000, credit_tier="Thin File", requested_tenure_years=4, has_cosigner=True)
    offers = get_ranked_offers(app)
    eligible_ids = {o.partner_id for o in offers if o.eligible}
    assert eligible_ids == {"campuscredit_coop"}
    cc = offer_for("campuscredit_coop", offers)
    assert cc.requires_cosigner is True


def test_fair_credit_does_not_need_cosigner_at_campuscredit():
    app = Applicant(requested_amount=200_000, credit_tier="Fair", requested_tenure_years=5, has_cosigner=False)
    offers = get_ranked_offers(app)
    cc = offer_for("campuscredit_coop", offers)
    assert cc.eligible is True
    assert cc.requires_cosigner is False


def test_excellent_credit_gets_each_eligible_partners_best_rate():
    app = Applicant(requested_amount=500_000, credit_tier="Excellent", requested_tenure_years=5)
    offers = get_ranked_offers(app)
    ng = offer_for("nextgen_education", offers)
    assert ng.eligible is True  # 500k is within NextGen's 200k-2.5M range
    assert ng.estimated_rate_pct == next(p for p in PARTNERS if p.id == "nextgen_education").best_rate_pct

    sb = offer_for("scholarbridge_finance", offers)
    assert sb.eligible is True
    assert sb.estimated_rate_pct == next(p for p in PARTNERS if p.id == "scholarbridge_finance").best_rate_pct


def test_amount_outside_every_partner_range_is_rejected_everywhere():
    app = Applicant(requested_amount=10_000, credit_tier="Excellent", requested_tenure_years=3)
    offers = get_ranked_offers(app)
    assert all(not o.eligible for o in offers)


def test_offers_are_ranked_by_ascending_rate():
    app = Applicant(requested_amount=500_000, credit_tier="Excellent", requested_tenure_years=5)
    offers = [o for o in get_ranked_offers(app) if o.eligible]
    rates = [o.estimated_rate_pct for o in offers]
    assert rates == sorted(rates), "Eligible offers must be ranked cheapest-first"


def test_tenure_ceiling_enforced():
    app = Applicant(requested_amount=500_000, credit_tier="Excellent", requested_tenure_years=20)
    offers = get_ranked_offers(app)
    assert all(not o.eligible for o in offers), "No partner offers 20-year tenure"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"FAIL: {t.__name__} -- {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
