import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getJSON, listingToRequest, postJSON } from "../api";
import Analysis from "../components/Analysis";
import { loadBuyer, loadShortlist, toggleShortlist } from "../storage";

export default function Listing() {
  const { id } = useParams();
  const [listing, setListing] = useState(null);
  const [note, setNote] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(() => loadShortlist().includes(id));
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setSaved(loadShortlist().includes(id));
    setResult(null);
    setError("");
    getJSON(`/listings/${id}`)
      .then((body) => {
        setListing(body.listing);
        setNote(body.note);
      })
      .catch((exc) => setError(exc.message));
  }, [id]);

  useEffect(() => {
    if (!listing) return undefined;
    let cancelled = false;
    async function run() {
      setBusy(true);
      try {
        const analysis = await postJSON("/analyze", listingToRequest(listing, loadBuyer()));
        if (!cancelled) {
          setResult(analysis);
          setError("");
        }
      } catch (exc) {
        if (!cancelled) setError(exc.message);
      } finally {
        if (!cancelled) setBusy(false);
      }
    }
    run();
    const refresh = () => run();
    window.addEventListener("hometruth-buyer", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("hometruth-buyer", refresh);
    };
  }, [listing]);

  async function download() {
    if (!result) return;
    const response = await fetch("/report", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(result),
    });
    if (!response.ok) {
      setError("The PDF could not be built.");
      return;
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "hometruth-estimate.pdf";
    link.click();
    URL.revokeObjectURL(url);
  }

  function onSave() {
    try {
      toggleShortlist(id);
      setSaved(loadShortlist().includes(id));
      setError("");
    } catch (exc) {
      setError(exc.message);
    }
  }

  if (!listing && !error) return <p>Loading listing…</p>;
  if (!listing) return <p className="callout">{error}</p>;

  return (
    <section>
      <p className="eyebrow">
        <Link to={`/locality/${encodeURIComponent(listing.locality)}`}>{listing.locality}</Link>
      </p>
      <h1>
        {listing.bhk} BHK, {Math.round(listing.total_sqft)} sqft
      </h1>
      <p className="muted">{note}</p>
      <p>
        {listing.area_type}. {listing.ready_to_move ? "Ready to move." : "Not marked ready to move."}{" "}
        {listing.bath} bathrooms.
      </p>
      <div className="actions">
        <button type="button" className="primary" onClick={onSave}>
          {saved ? "Remove from shortlist" : "Add to shortlist"}
        </button>
        <button type="button" className="ghost" onClick={download} disabled={!result}>Download PDF</button>
      </div>
      {error ? <p className="callout">{error}</p> : null}
      {busy && !result ? <p>Estimating price, costs, and location…</p> : null}
      <Analysis result={result} />
    </section>
  );
}
