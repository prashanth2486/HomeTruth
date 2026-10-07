"""Buyer-side estimate for one Bengaluru listing."""

import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
load_dotenv(ROOT / ".env")

from chat import respond
from formatting import format_inr
from model_frame import default_area_type
from predict import analyze, load_artifact
from rates import DISCLAIMER, RATE_NOTES
from report import build_pdf
from schemas import (
    AnalysisResult,
    AnalyzeRequest,
    Assumptions,
    BuyerInput,
    ChatMessage,
    ChatRequest,
    ListingInput,
)
from validation import InputError
from verdict import VERDICT_LABELS

st.set_page_config(page_title="HomeTruth", layout="wide")


def _artifact():
    try:
        return load_artifact()
    except FileNotFoundError as exc:
        st.error(str(exc))
        st.stop()


def _listing_inputs(artifact) -> ListingInput:
    localities = list(artifact["locality_categories"]) + ["Other"]
    default_index = localities.index("Whitefield") if "Whitefield" in localities else 0
    choice = st.selectbox("Locality", localities, index=default_index)
    custom = ""
    if choice == "Other":
        custom = st.text_input("Locality name", placeholder="A neighbourhood in Bengaluru")
    locality = custom.strip() if choice == "Other" else choice
    total_sqft = st.number_input("Area (sqft)", min_value=100.0, max_value=20000.0, value=1200.0, step=10.0)
    bhk = st.number_input("BHK", min_value=1, max_value=10, value=2, step=1)
    bath = st.number_input("Bathrooms", min_value=1.0, max_value=10.0, value=2.0, step=1.0)
    area_types = list(artifact["area_types"])
    preferred = default_area_type(area_types)
    area_type = st.selectbox("Area type", area_types, index=area_types.index(preferred))
    under_construction = st.checkbox("Under construction")
    first_sale = st.checkbox(
        "First sale of a flat",
        help="Check this for a new flat. First sales up to ₹45 lakh use a lower stamp-duty rate. Resales use 5%.",
    )
    carpet = st.number_input(
        "Carpet area (sqft, optional)",
        min_value=0.0,
        max_value=20000.0,
        value=0.0,
        step=10.0,
        help="Used for the GST affordable-housing test. Leave at 0 to assume 70% of the area above.",
    )
    asking_lakh = st.number_input("Asking price (₹ lakh)", min_value=1.0, max_value=50000.0, value=80.0, step=1.0)
    return ListingInput(
        locality=locality or "Other",
        total_sqft=float(total_sqft),
        bhk=int(bhk),
        bath=float(bath),
        area_type=area_type,
        ready_to_move=not under_construction,
        first_sale=bool(first_sale),
        asking_price_inr=float(asking_lakh) * 100_000,
        carpet_sqft=None if carpet <= 0 else float(carpet),
    )


def _buyer_inputs() -> tuple[BuyerInput, str, Assumptions]:
    income = st.number_input("Net monthly income (₹)", min_value=1.0, value=150000.0, step=5000.0)
    existing = st.number_input("Existing monthly EMIs (₹)", min_value=0.0, value=0.0, step=1000.0)
    down_payment = st.slider("Down payment", min_value=0.10, max_value=0.80, value=0.20, step=0.05)
    rate_pct = st.slider("Interest rate (%)", min_value=6.0, max_value=15.0, value=8.0, step=0.05)
    tenure = st.slider("Loan tenure (years)", min_value=1, max_value=30, value=20)
    emi_cap = st.slider("EMI cap (share of net income)", min_value=0.40, max_value=0.50, value=0.40, step=0.01)
    office = st.text_input("Office address (optional)", value="Manyata Tech Park, Bengaluru")
    with st.expander("Buy versus rent assumptions"):
        appreciation = st.slider("Price appreciation per year", 0.0, 0.15, 0.05, 0.01)
        rent_growth = st.slider("Rent growth per year", 0.0, 0.15, 0.05, 0.01)
        investment = st.slider("Return if you invested the cash", 0.0, 0.15, 0.07, 0.01)
        maintenance = st.slider("Maintenance per year, share of value", 0.0, 0.03, 0.005, 0.001)
        st.caption("Rent uses an indicative yield, not a listed rent. Change it only if you have a better figure.")
        custom_yield = st.checkbox("Set my own gross yield")
        gross_yield = None
        if custom_yield:
            gross_yield = st.slider("Gross annual rent / price", 0.0, 0.08, 0.03, 0.005)
    buyer = BuyerInput(
        net_monthly_income_inr=float(income),
        existing_monthly_emi_inr=float(existing),
        down_payment_fraction=float(down_payment),
        annual_interest_rate=float(rate_pct) / 100,
        tenure_years=int(tenure),
        emi_ratio_cap=float(emi_cap),
    )
    assumptions = Assumptions(
        appreciation=float(appreciation),
        rent_growth=float(rent_growth),
        investment_return=float(investment),
        maintenance_rate=float(maintenance),
        gross_yield=None if gross_yield is None else float(gross_yield),
    )
    return buyer, office.strip(), assumptions


def _money_row(label: str, amount: float) -> None:
    st.write(f"{label}: {format_inr(amount)}")


def _render_analysis(payload: dict) -> None:
    result = AnalysisResult.model_validate(payload)
    verdict = result.price.verdict
    label = VERDICT_LABELS[verdict]
    if verdict == "great_deal":
        st.success(label)
    elif verdict == "overpriced":
        st.error(label)
    else:
        st.info(label)
    left, middle, right = st.columns(3)
    left.metric("Asking price", format_inr(result.price.asking_inr))
    middle.metric("Mid estimate", format_inr(result.price.p50_inr))
    right.metric(
        "Suggested offer",
        f"{format_inr(result.price.offer_low_inr)} – {format_inr(result.price.offer_high_inr)}",
    )
    st.write(
        f"Fair range (10th to 90th): {format_inr(result.price.p10_inr)} to {format_inr(result.price.p90_inr)}."
    )
    if result.price.locality_unseen:
        st.warning("This locality is outside the areas the model saw often. Treat the range as less reliable.")
    st.write(result.price.explanation)

    cost_col, budget_col = st.columns(2)
    with cost_col:
        st.subheader("What you pay")
        _money_row("Stamp duty, including cess and surcharge", result.costs.stamp_duty_inr)
        _money_row("Registration", result.costs.registration_inr)
        _money_row("GST", result.costs.gst_inr)
        _money_row("Loan interest over the full tenure", result.costs.total_interest_inr)
        _money_row("All-in cost", result.costs.all_in_cost_inr)
        _money_row("Cash at purchase", result.costs.due_at_purchase_inr)
        st.caption(result.costs.gst_note)
        st.caption(result.costs.guidance_value_note)
    with budget_col:
        st.subheader("Can you afford it?")
        fit = "Fits the EMI rule" if result.affordability.fits else "Above the EMI rule"
        st.write(fit)
        _money_row("Monthly EMI", result.affordability.emi_inr)
        _money_row("EMI cap", result.affordability.max_emi_inr)
        _money_row("Maximum loan", result.affordability.max_loan_inr)
        _money_row("Price that loan can support", result.affordability.max_affordable_price_inr)
        st.caption(result.affordability.reason)
        st.caption("Income is used for this check and is not saved.")

    st.subheader("Buy versus rent")
    st.caption(result.rent_note)
    st.caption(f"Indicative rent: {format_inr(result.rent_monthly_inr)} per month.")
    st.caption(result.assumptions_note)
    table = []
    for row in result.buy_vs_rent:
        table.append(
            {
                "Years": row.years,
                "Higher net worth": row.cheaper,
                "Buyer net worth": format_inr(row.buyer_net_worth_inr),
                "Renter net worth": format_inr(row.renter_net_worth_inr),
                "Cash spent if buying": format_inr(row.buy_cash_outflow_inr),
                "Rent paid": format_inr(row.rent_cash_outflow_inr),
            }
        )
    st.dataframe(table, width="stretch", hide_index=True)

    st.subheader("Location")
    if result.location.available and result.location.locality_score is not None:
        st.metric("Locality score", f"{result.location.locality_score:.0f} / 100")
        if result.location.components:
            component_rows = []
            for name, component in result.location.components.items():
                nearest = "—" if component.nearest_m is None else f"{component.nearest_m:.0f} m"
                component_rows.append(
                    {
                        "Place": name.replace("_", " "),
                        "Count within 2 km": component.count,
                        "Nearest": nearest,
                        "Score": round(component.score),
                    }
                )
            st.dataframe(component_rows, width="stretch", hide_index=True)
        if result.location.commute_minutes is not None and result.location.commute_km is not None:
            st.write(
                f"Commute: {result.location.commute_minutes:.0f} minutes, {result.location.commute_km:.1f} km "
                f"at {result.location.commute_speed_kmh:.0f} km/h."
            )
    st.caption(result.location.note)

    actions = st.columns(2)
    pdf = build_pdf(result)
    actions[0].download_button(
        "Download PDF",
        data=pdf,
        file_name="hometruth-estimate.pdf",
        mime="application/pdf",
    )
    if actions[1].button("Add to compare"):
        shortlist = st.session_state["shortlist"]
        if len(shortlist) >= 3:
            st.warning("Compare holds 3 listings. Remove one first.")
        else:
            shortlist.append(payload)
            st.session_state["shortlist"] = shortlist
            st.success("Added to Compare.")


def _render_compare() -> None:
    shortlist = st.session_state["shortlist"]
    if not shortlist:
        st.info("Analyze a listing and add it here. Compare needs 2 or 3 properties.")
        return
    if len(shortlist) == 1:
        st.info("One listing is saved. Add another to compare them side by side.")
    columns = st.columns(len(shortlist))
    for index, (column, payload) in enumerate(zip(columns, shortlist, strict=True)):
        result = AnalysisResult.model_validate(payload)
        with column:
            st.subheader(result.locality_entered)
            st.write(VERDICT_LABELS[result.price.verdict])
            st.write(f"Asking {format_inr(result.price.asking_inr)}")
            st.write(f"Range {format_inr(result.price.p10_inr)} – {format_inr(result.price.p90_inr)}")
            st.write(f"All-in {format_inr(result.costs.all_in_cost_inr)}")
            st.write("Fits EMI rule" if result.affordability.fits else "Above EMI rule")
            if result.location.locality_score is not None:
                st.write(f"Locality score {result.location.locality_score:.0f}")
            if result.location.commute_minutes is not None:
                st.write(f"Commute {result.location.commute_minutes:.0f} min")
            else:
                st.write("No commute time")
            if st.button("Remove", key=f"remove_{index}"):
                del st.session_state["shortlist"][index]
                st.rerun()


def _render_chat() -> None:
    if "result" not in st.session_state:
        st.info("Run an analysis first. The assistant only talks about that result.")
        return
    result = AnalysisResult.model_validate(st.session_state["result"])
    used = sum(1 for item in st.session_state["messages"] if item["role"] == "user")
    st.caption(f"{max(0, 12 - used)} questions left in this analysis. The assistant cannot see your income.")
    for item in st.session_state["messages"]:
        with st.chat_message(item["role"]):
            st.write(item["content"])
    question = st.chat_input("Ask about this estimate")
    if not question:
        return
    history = [ChatMessage(role=item["role"], content=item["content"]) for item in st.session_state["messages"]]
    reply = respond(ChatRequest(analysis=result, messages=history, user_message=question))
    st.session_state["messages"].append({"role": "user", "content": question})
    st.session_state["messages"].append({"role": "assistant", "content": reply.text})
    st.rerun()


def main() -> None:
    st.session_state.setdefault("shortlist", [])
    st.session_state.setdefault("messages", [])
    st.title("HomeTruth")
    st.caption(DISCLAIMER)
    artifact = _artifact()
    with st.sidebar:
        st.header("Listing")
        listing = _listing_inputs(artifact)
        st.header("Your numbers")
        st.caption("Income and office location stay in this session. They are not saved.")
        buyer, office, assumptions = _buyer_inputs()
        run = st.button("Analyze", type="primary")
        with st.expander("How the charges are calculated"):
            for note in RATE_NOTES:
                st.write(note)
    if run:
        if not listing.locality.strip() or listing.locality == "Other":
            st.error("Enter a locality.")
        else:
            try:
                with st.spinner("Estimating the price, costs, and location"):
                    result = analyze(
                        AnalyzeRequest(
                            listing=listing,
                            buyer=buyer,
                            office_address=office or None,
                            assumptions=assumptions,
                        )
                    )
            except InputError as exc:
                st.error(str(exc))
            else:
                st.session_state["result"] = result.model_dump(mode="json")
                st.session_state["messages"] = []
    analyze_tab, compare_tab, chat_tab = st.tabs(["Analyze", "Compare", "Assistant"])
    with analyze_tab:
        if "result" not in st.session_state:
            st.write("Enter a listing and choose Analyze. Start with the Whitefield example already filled in.")
        else:
            _render_analysis(st.session_state["result"])
    with compare_tab:
        _render_compare()
    with chat_tab:
        _render_chat()


if __name__ == "__main__":
    main()
else:
    main()
