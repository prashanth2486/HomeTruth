import { inr, verdictLabel } from "../format";

function Row({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function Analysis({ result }) {
  if (!result) return null;
  const price = result.price;
  const costs = result.costs;
  const budget = result.affordability;
  return (
    <div className="analysis">
      <p className={`pill ${price.verdict}`}>{verdictLabel(price.verdict)}</p>
      <div className="stat-grid">
        <Row label="Asking price" value={inr(price.asking_inr)} />
        <Row label="Mid estimate" value={inr(price.p50_inr)} />
        <Row label="Suggested offer" value={`${inr(price.offer_low_inr)} – ${inr(price.offer_high_inr)}`} />
      </div>
      <p>
        Fair range (10th to 90th): {inr(price.p10_inr)} to {inr(price.p90_inr)}.
      </p>
      <p>{price.explanation}</p>
      {price.locality_unseen ? (
        <p className="callout">This locality was grouped as “other”, so the price estimate is less reliable.</p>
      ) : null}

      <h3>What you pay</h3>
      <div className="stat-grid">
        <Row label="Stamp duty" value={inr(costs.stamp_duty_inr)} />
        <Row label="Registration" value={inr(costs.registration_inr)} />
        <Row label="GST" value={inr(costs.gst_inr)} />
        <Row label="Loan interest" value={inr(costs.total_interest_inr)} />
        <Row label="All-in cost" value={inr(costs.all_in_cost_inr)} />
        <Row label="Cash at purchase" value={inr(costs.due_at_purchase_inr)} />
      </div>
      <p className="muted">{costs.gst_note}</p>
      <p className="muted">{costs.guidance_value_note}</p>

      <h3>Can you afford it?</h3>
      <p className={budget.fits ? "pill fair" : "pill overpriced"}>
        {budget.fits ? "Fits the EMI rule" : "Above the EMI rule"}
      </p>
      <div className="stat-grid">
        <Row label="Monthly EMI" value={inr(budget.emi_inr)} />
        <Row label="EMI cap" value={inr(budget.max_emi_inr)} />
        <Row label="Maximum loan" value={inr(budget.max_loan_inr)} />
        <Row label="Price that loan can support" value={inr(budget.max_affordable_price_inr)} />
      </div>
      <p>{budget.reason}</p>
      <p className="muted">Income is used for this check and is not saved.</p>

      <h3>Buy versus rent</h3>
      <p className="muted">{result.rent_note}</p>
      <p>Indicative rent: {inr(result.rent_monthly_inr)} per month.</p>
      <p className="muted">{result.assumptions_note}</p>
      <table>
        <thead>
          <tr>
            <th>Years</th>
            <th>Higher net worth</th>
            <th>Buyer</th>
            <th>Renter</th>
          </tr>
        </thead>
        <tbody>
          {result.buy_vs_rent.map((row) => (
            <tr key={row.years}>
              <td>{row.years}</td>
              <td>{row.cheaper}</td>
              <td>{inr(row.buyer_net_worth_inr)}</td>
              <td>{inr(row.renter_net_worth_inr)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Location</h3>
      {result.location.available && result.location.locality_score != null ? (
        <>
          <p className="score">{Math.round(result.location.locality_score)} / 100</p>
          {result.location.commute_minutes != null ? (
            <p>
              Commute: {Math.round(result.location.commute_minutes)} minutes,{" "}
              {Number(result.location.commute_km).toFixed(1)} km at {Math.round(result.location.commute_speed_kmh)} km/h.
            </p>
          ) : null}
        </>
      ) : null}
      <p className="muted">{result.location.note}</p>
    </div>
  );
}
