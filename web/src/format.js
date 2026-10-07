export function inr(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const amount = Number(value);
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "−" : "";
  if (abs >= 1e7) return `${sign}₹${(abs / 1e7).toFixed(2)} crore`;
  if (abs >= 1e5) return `${sign}₹${(abs / 1e5).toFixed(2)} lakh`;
  return `${sign}₹${Math.round(abs).toLocaleString("en-IN")}`;
}

export function verdictLabel(verdict) {
  if (verdict === "great_deal") return "Great deal";
  if (verdict === "overpriced") return "Overpriced";
  return "Fair";
}

export function pct(share) {
  return `${Math.round(Number(share) * 100)}%`;
}
