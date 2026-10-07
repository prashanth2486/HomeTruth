import { useEffect, useState } from "react";

import { useAuth } from "../auth";
import { loadBuyer, saveBuyer } from "../storage";

function toForm(buyer) {
  const rate = Number(buyer.annual_interest_rate);
  return { ...buyer, annual_interest_rate: rate <= 1 ? rate * 100 : rate };
}

export default function BuyerPanel({ open, onClose }) {
  const { signedIn } = useAuth();
  const [buyer, setBuyer] = useState(() => toForm(loadBuyer()));

  useEffect(() => {
    if (open) setBuyer(toForm(loadBuyer()));
  }, [open]);

  if (!open) return null;

  function update(field, value) {
    setBuyer((current) => ({ ...current, [field]: value }));
  }

  function apply(event) {
    event.preventDefault();
    saveBuyer({
      ...buyer,
      net_monthly_income_inr: Number(buyer.net_monthly_income_inr),
      existing_monthly_emi_inr: Number(buyer.existing_monthly_emi_inr),
      down_payment_fraction: Number(buyer.down_payment_fraction),
      annual_interest_rate: Number(buyer.annual_interest_rate) / 100,
      tenure_years: Number(buyer.tenure_years),
      emi_ratio_cap: Number(buyer.emi_ratio_cap),
    });
    onClose();
  }

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <form className="drawer" onClick={(event) => event.stopPropagation()} onSubmit={apply}>
        <header className="drawer-head">
          <h2>Your numbers</h2>
          <button type="button" className="text-button" onClick={onClose}>Close</button>
        </header>
        <p className="muted">
          {signedIn
            ? "Signed in: these numbers sync to your account. They are never written to the prediction log."
            : "Guest mode: income and office stay in this browser tab only. Sign in to sync them."}
        </p>
        <label>
          Net monthly income (₹)
          <input
            type="number"
            min="1"
            value={buyer.net_monthly_income_inr}
            onChange={(event) => update("net_monthly_income_inr", event.target.value)}
          />
        </label>
        <label>
          Existing monthly EMIs (₹)
          <input
            type="number"
            min="0"
            value={buyer.existing_monthly_emi_inr}
            onChange={(event) => update("existing_monthly_emi_inr", event.target.value)}
          />
        </label>
        <label>
          Down payment ({Math.round(Number(buyer.down_payment_fraction) * 100)}%)
          <input
            type="range"
            min="0.1"
            max="0.8"
            step="0.05"
            value={buyer.down_payment_fraction}
            onChange={(event) => update("down_payment_fraction", event.target.value)}
          />
        </label>
        <label>
          Interest rate ({Number(buyer.annual_interest_rate).toFixed(2)}%)
          <input
            type="range"
            min="6"
            max="15"
            step="0.05"
            value={buyer.annual_interest_rate}
            onChange={(event) => update("annual_interest_rate", event.target.value)}
          />
        </label>
        <label>
          Loan tenure ({buyer.tenure_years} years)
          <input
            type="range"
            min="1"
            max="30"
            step="1"
            value={buyer.tenure_years}
            onChange={(event) => update("tenure_years", event.target.value)}
          />
        </label>
        <label>
          EMI cap ({Math.round(Number(buyer.emi_ratio_cap) * 100)}% of income)
          <input
            type="range"
            min="0.4"
            max="0.5"
            step="0.01"
            value={buyer.emi_ratio_cap}
            onChange={(event) => update("emi_ratio_cap", event.target.value)}
          />
        </label>
        <label>
          Office address
          <input
            value={buyer.office_address}
            onChange={(event) => update("office_address", event.target.value)}
          />
        </label>
        <button className="primary" type="submit">Use these numbers</button>
      </form>
    </div>
  );
}
