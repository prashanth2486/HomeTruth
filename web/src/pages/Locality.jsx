import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { getJSON } from "../api";
import { inr, pct } from "../format";
import { ListingRows } from "./Home";

export default function Locality() {
  const { name } = useParams();
  const decoded = decodeURIComponent(name);
  const [body, setBody] = useState(null);
  const [score, setScore] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setBody(null);
    setScore(null);
    getJSON(`/localities/${encodeURIComponent(decoded)}?limit=40`)
      .then(setBody)
      .catch((exc) => setError(exc.message));
    getJSON(`/localities/${encodeURIComponent(decoded)}/location`)
      .then(setScore)
      .catch(() => setScore({ available: false, note: "Location data is unavailable." }));
  }, [decoded]);

  if (error) return <p className="callout">{error}</p>;
  if (!body) return <p>Loading {decoded}…</p>;
  const place = body.locality;

  return (
    <section>
      <p className="eyebrow">Neighbourhood</p>
      <h1>{place.name}</h1>
      <p className="muted">{body.note}</p>
      <div className="stat-grid">
        <div className="stat"><span>Historical asks</span><strong>{place.count}</strong></div>
        <div className="stat"><span>Median ask</span><strong>{inr(place.median_asking_inr)}</strong></div>
        <div className="stat"><span>Median model price</span><strong>{inr(place.median_model_inr)}</strong></div>
        <div className="stat"><span>Share overpriced</span><strong>{pct(place.share_overpriced)}</strong></div>
      </div>
      <h2>Around this locality</h2>
      {score ? (
        score.available && score.locality_score != null ? (
          <p>Locality score {Math.round(score.locality_score)} / 100. {score.note}</p>
        ) : (
          <p className="muted">{score.note || "Looking up places nearby…"}</p>
        )
      ) : (
        <p className="muted">Looking up metro stations, schools, and hospitals…</p>
      )}
      <h2>Listings</h2>
      <ListingRows listings={body.listings} />
    </section>
  );
}
