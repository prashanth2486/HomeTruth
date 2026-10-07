import { useState } from "react";

import { postJSON } from "../api";
import Analysis from "../components/Analysis";
import { loadBuyer } from "../storage";

const EMPTY = {
  locality: "Whitefield",
  total_sqft: 1200,
  bhk: 2,
  bath: 2,
  area_type: "Super built-up Area",
  ready_to_move: true,
  first_sale: false,
  asking_lakh: 80,
  carpet_sqft: "",
};

export default function Check() {
  const [form, setForm] = useState(EMPTY);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const buyer = loadBuyer();
      const analysis = await postJSON("/analyze", {
        listing: {
          locality: form.locality,
          total_sqft: Number(form.total_sqft),
          bhk: Number(form.bhk),
          bath: Number(form.bath),
          area_type: form.area_type,
          ready_to_move: Boolean(form.ready_to_move),
          first_sale: Boolean(form.first_sale),
          asking_price_inr: Number(form.asking_lakh) * 100000,
          carpet_sqft: form.carpet_sqft ? Number(form.carpet_sqft) : null,
        },
        buyer: {
          net_monthly_income_inr: Number(buyer.net_monthly_income_inr),
          existing_monthly_emi_inr: Number(buyer.existing_monthly_emi_inr),
          down_payment_fraction: Number(buyer.down_payment_fraction),
          annual_interest_rate: Number(buyer.annual_interest_rate),
          tenure_years: Number(buyer.tenure_years),
          emi_ratio_cap: Number(buyer.emi_ratio_cap),
        },
        office_address: buyer.office_address?.trim() || null,
        assumptions: {
          appreciation: 0.05,
          rent_growth: 0.05,
          investment_return: 0.07,
          maintenance_rate: 0.005,
          gross_yield: null,
        },
      });
      setResult(analysis);
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <p className="eyebrow">Not in the catalog</p>
      <h1>Check a price</h1>
      <form className="check-form" onSubmit={submit}>
        <label>Locality<input value={form.locality} onChange={(event) => update("locality", event.target.value)} /></label>
        <label>Area (sqft)<input type="number" value={form.total_sqft} onChange={(event) => update("total_sqft", event.target.value)} /></label>
        <label>BHK<input type="number" value={form.bhk} onChange={(event) => update("bhk", event.target.value)} /></label>
        <label>Bathrooms<input type="number" value={form.bath} onChange={(event) => update("bath", event.target.value)} /></label>
        <label>
          Area type
          <select value={form.area_type} onChange={(event) => update("area_type", event.target.value)}>
            <option>Super built-up Area</option>
            <option>Built-up Area</option>
            <option>Plot Area</option>
            <option>Carpet Area</option>
          </select>
        </label>
        <label>Asking price (₹ lakh)<input type="number" value={form.asking_lakh} onChange={(event) => update("asking_lakh", event.target.value)} /></label>
        <label>Carpet area (sqft, optional)<input type="number" value={form.carpet_sqft} onChange={(event) => update("carpet_sqft", event.target.value)} /></label>
        <label className="check">
          <input type="checkbox" checked={form.ready_to_move} onChange={(event) => update("ready_to_move", event.target.checked)} />
          Ready to move
        </label>
        <label className="check">
          <input type="checkbox" checked={form.first_sale} onChange={(event) => update("first_sale", event.target.checked)} />
          First sale of a flat
        </label>
        <button className="primary" type="submit" disabled={busy}>{busy ? "Estimating…" : "Estimate"}</button>
      </form>
      {error ? <p className="callout">{error}</p> : null}
      <Analysis result={result} />
    </section>
  );
}
