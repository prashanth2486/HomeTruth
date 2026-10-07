"""In-memory PDF summary. Nothing is written to disk."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from formatting import format_inr_pdf
from rates import DISCLAIMER
from schemas import AnalysisResult
from verdict import VERDICT_LABELS


def _p(text: str, style) -> Paragraph:
    return Paragraph(escape(text), style)


def build_pdf(result: AnalysisResult) -> bytes:
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="HomeTruth estimate",
    )
    styles = getSampleStyleSheet()
    story = [
        _p("HomeTruth estimate", styles["Title"]),
        _p(DISCLAIMER, styles["Italic"]),
        Spacer(1, 8),
        _p(
            f"{result.locality_entered}: {result.bhk} BHK, {result.total_sqft:.0f} sqft, "
            f"{result.bath:g} bath, {result.area_type}.",
            styles["Normal"],
        ),
        _p(f"Verdict: {VERDICT_LABELS[result.price.verdict]}", styles["Heading2"]),
        _p(
            f"Asking price {format_inr_pdf(result.price.asking_inr)}. "
            f"Estimated range {format_inr_pdf(result.price.p10_inr)} to {format_inr_pdf(result.price.p90_inr)}. "
            f"Mid estimate {format_inr_pdf(result.price.p50_inr)}. "
            f"Suggested offer {format_inr_pdf(result.price.offer_low_inr)} to {format_inr_pdf(result.price.offer_high_inr)}.",
            styles["Normal"],
        ),
        _p(result.price.explanation, styles["Normal"]),
        Spacer(1, 6),
        _p("What it costs", styles["Heading2"]),
        _p(
            f"Stamp duty {format_inr_pdf(result.costs.stamp_duty_inr)} "
            f"(base {format_inr_pdf(result.costs.stamp_duty_base_inr)}, "
            f"cess {format_inr_pdf(result.costs.cess_inr)}, "
            f"surcharge {format_inr_pdf(result.costs.surcharge_inr)}). "
            f"Registration {format_inr_pdf(result.costs.registration_inr)}. "
            f"GST {format_inr_pdf(result.costs.gst_inr)}. "
            f"Loan interest {format_inr_pdf(result.costs.total_interest_inr)}. "
            f"All-in over the loan tenure {format_inr_pdf(result.costs.all_in_cost_inr)}. "
            f"Cash at purchase {format_inr_pdf(result.costs.due_at_purchase_inr)}.",
            styles["Normal"],
        ),
        _p(result.costs.gst_note, styles["Normal"]),
        _p(result.costs.guidance_value_note, styles["Normal"]),
        Spacer(1, 6),
        _p("Affordability", styles["Heading2"]),
        _p(
            f"EMI {format_inr_pdf(result.affordability.emi_inr)} against a cap of "
            f"{format_inr_pdf(result.affordability.max_emi_inr)}. "
            f"Maximum loan {format_inr_pdf(result.affordability.max_loan_inr)}. "
            f"Purchase price supported by that loan: up to {format_inr_pdf(result.affordability.max_affordable_price_inr)}. "
            f"{'The listing fits the EMI rule.' if result.affordability.fits else 'The listing is above the EMI rule.'} "
            f"{result.affordability.reason}",
            styles["Normal"],
        ),
        Spacer(1, 6),
        _p("Buy versus rent", styles["Heading2"]),
        _p(result.assumptions_note, styles["Normal"]),
        _p(result.rent_note + f" Indicative rent {format_inr_pdf(result.rent_monthly_inr)} per month.", styles["Normal"]),
    ]
    for row in result.buy_vs_rent:
        story.append(
            _p(
                f"After {row.years} years, {row.cheaper} leaves the higher net worth "
                f"(buy {format_inr_pdf(row.buyer_net_worth_inr)}, rent {format_inr_pdf(row.renter_net_worth_inr)}).",
                styles["Normal"],
            )
        )
    story.extend(
        [
            Spacer(1, 6),
            _p("Location", styles["Heading2"]),
            _p(result.location.note, styles["Normal"]),
        ]
    )
    if result.location.available and result.location.locality_score is not None:
        story.append(_p(f"Locality score {result.location.locality_score:.0f} out of 100.", styles["Normal"]))
    if result.location.commute_minutes is not None and result.location.commute_km is not None:
        story.append(
            _p(
                f"Commute {result.location.commute_minutes:.0f} minutes, {result.location.commute_km:.1f} km.",
                styles["Normal"],
            )
        )
    story.extend([Spacer(1, 10), _p(result.disclaimer, styles["Italic"])])
    document.build(story)
    return buffer.getvalue()
