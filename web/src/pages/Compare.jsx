import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getJSON, listingToRequest, postJSON } from "../api";
import { inr, verdictLabel } from "../format";
import { loadBuyer, loadShortlist } from "../storage";

export default function Compare() {
  const [columns, setColumns] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const ids = loadShortlist();
    if (ids.length < 2) {
      setColumns([]);
      return undefined;
    }
    let cancelled = false;
    let generation = 0;
    async function run() {
      const mine = ++generation;
      setBusy(true);
      try {
        const rows = await Promise.all(ids.slice(0, 3).map((id) => getJSON(`/listings/${id}`)));
        const listings = rows.map((row) => row.listing);
        const buyer = loadBuyer();
        const compared = await postJSON("/compare", {
          listings: listings.map((item) => listingToRequest(item, buyer).listing),
          buyer: listingToRequest(listings[0], buyer).buyer,
          office_address: buyer.office_address?.trim() || null,
          assumptions: listingToRequest(listings[0], buyer).assumptions,
        });
        if (cancelled || mine !== generation) return;
        setColumns(listings.map((item, index) => ({ item, result: compared.results[index] })));
        setError("");
      } catch (exc) {
        if (!cancelled && mine === generation) setError(exc.message);
      } finally {
        if (!cancelled && mine === generation) setBusy(false);
      }
    }
    run();
    window.addEventListener("hometruth-buyer", run);
    return () => {
      cancelled = true;
      window.removeEventListener("hometruth-buyer", run);
    };
  }, []);

  const ids = loadShortlist();

  return (
    <section>
      <p className="eyebrow">Side by side</p>
      <h1>Compare</h1>
      {ids.length < 2 ? (
        <p>Add at least two homes on the <Link to="/shortlist">shortlist</Link>.</p>
      ) : null}
      {busy ? <p>Comparing price, cost, and commute…</p> : null}
      {error ? <p className="callout">{error}</p> : null}
      <div className="card-row">
        {columns.map(({ item, result }) => (
          <article key={item.id} className="card static">
            <strong>{item.locality}</strong>
            <span>{verdictLabel(result.price.verdict)}</span>
            <span>Ask {inr(result.price.asking_inr)}</span>
            <span>Range {inr(result.price.p10_inr)} – {inr(result.price.p90_inr)}</span>
            <span>All-in {inr(result.costs.all_in_cost_inr)}</span>
            <span>{result.affordability.fits ? "Fits EMI rule" : "Above EMI rule"}</span>
            <span>
              {result.location.locality_score != null
                ? `Locality score ${Math.round(result.location.locality_score)}`
                : "No locality score"}
            </span>
            <span>
              {result.location.commute_minutes != null
                ? `Commute ${Math.round(result.location.commute_minutes)} min`
                : "No commute time"}
            </span>
            <Link to={`/listing/${item.id}`}>Open</Link>
          </article>
        ))}
      </div>
    </section>
  );
}
