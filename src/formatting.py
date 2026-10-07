"""Display helpers for rupee amounts."""


def format_inr(amount: float, symbol: str = "₹") -> str:
    sign = "-" if amount < 0 else ""
    value = abs(float(amount))
    if value >= 1_00_00_000:
        text = f"{value / 1_00_00_000:.2f} crore"
    elif value >= 1_00_000:
        text = f"{value / 1_00_000:.2f} lakh"
    else:
        text = f"{value:,.0f}"
    return f"{sign}{symbol}{text}"


def format_inr_pdf(amount: float) -> str:
    """ReportLab's standard fonts do not include the rupee sign."""
    return format_inr(amount, symbol="Rs ")
