"""Karnataka buyer costs and calculator defaults.

Figures were checked on 7 October 2026. Confirm them before a real purchase.
Stamp duty follows the Karnataka Stamp Act, Article 20. The 2% and 3% bands
apply to the first sale of a flat; other transfers use 5%. Cess is 10% of the
duty and the BBMP surcharge is 2% of the duty. Registration is 2% of the
property value from 31 August 2025 (notification RD/46/MNMU/2025).

GST on under-construction residential apartments is the effective 1% or 5%
rate in force since 1 April 2019, without input tax credit. Affordable means
carpet area up to 60 sq m in a metro such as Bengaluru and a price up to
₹45 lakh.

The default loan rate sits inside the SBI home-loan band of 7.25% to 8.55%
reported for October 2026. It is a starting point, not a bank quote.
"""

RATES_AS_OF = "2026-10-07"

STAMP_DUTY_STANDARD = 0.05
STAMP_FIRST_SALE_UP_TO_20_LAKH = 0.02
STAMP_FIRST_SALE_UP_TO_45_LAKH = 0.03
FIRST_SALE_BAND_20_LAKH_INR = 2_000_000
FIRST_SALE_BAND_45_LAKH_INR = 4_500_000
CESS_ON_DUTY = 0.10
BBMP_SURCHARGE_ON_DUTY = 0.02
REGISTRATION_FEE = 0.02

GST_AFFORDABLE = 0.01
GST_STANDARD = 0.05
AFFORDABLE_PRICE_CAP_INR = 4_500_000
AFFORDABLE_CARPET_SQM = 60.0
SQFT_PER_SQM = 10.76391041671
CARPET_SHARE_OF_SUPER_BUILTUP = 0.70

DEFAULT_ANNUAL_INTEREST_RATE = 0.08
DEFAULT_TENURE_YEARS = 20
DEFAULT_DOWN_PAYMENT_FRACTION = 0.20
DEFAULT_EMI_RATIO = 0.40
MIN_EMI_RATIO = 0.40
MAX_EMI_RATIO = 0.50

DEFAULT_APPRECIATION = 0.05
DEFAULT_RENT_GROWTH = 0.05
DEFAULT_INVESTMENT_RETURN = 0.07
DEFAULT_MAINTENANCE_RATE = 0.005
DEFAULT_GROSS_YIELD = 0.03

LOCALITY_RADIUS_M = 2000
LOCALITY_WEIGHTS = {
    "metro": 35,
    "it_parks": 25,
    "schools": 20,
    "hospitals": 20,
}
COMMUTE_SPEED_KMH = 25.0
MIN_LOCALITY_COUNT = 10

CHAT_USER_MESSAGE_CAP = 12
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"

DISCLAIMER = (
    "HomeTruth is an estimate only. It is not an official valuation, a loan offer, "
    "or legal advice. Asking prices, not registered sale prices, trained the model. "
    "Rent, appreciation, and the locality score are indicative. The commute time "
    "ignores live traffic."
)

GUIDANCE_VALUE_NOTE = (
    "Stamp duty is legally calculated on the higher of the price and the government "
    "guidance value. This app does not have guidance values, so the duty here uses "
    "the price you entered. Confirm the figure with the sub-registrar."
)

RATE_NOTES = [
    "Stamp duty: 5% of price, except the first sale of a flat (2% up to ₹20 lakh, 3% up to ₹45 lakh, 5% above that). The rate applies to the whole price.",
    "Add cess of 10% of the duty and a BBMP surcharge of 2% of the duty.",
    "Registration fee: 2% of price, in force from 31 August 2025 (RD/46/MNMU/2025).",
    GUIDANCE_VALUE_NOTE,
    "GST: 1% for an affordable under-construction apartment (carpet up to 60 sq m and price up to ₹45 lakh), otherwise 5%. Ready property: no GST.",
    "Default interest is 8.0%, inside the SBI home-loan band of 7.25–8.55% reported for October 2026. Change it to your bank's rate.",
    f"Rates checked {RATES_AS_OF}.",
]
