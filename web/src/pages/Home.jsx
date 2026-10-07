import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getJSON } from "../api";
import MapView from "../components/MapView";
import { inr, pct } from "../format";

export default function Home() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [bhk, setBhk] = useState("");
  const [verdict, setVerdict] = useState("");
  const [maxLakh, setMaxLakh] = useState("");
  const [localities, setLocalities] = useState([]);
  const [pins, setPins] = useState([]);
  const [listings, setListings] = useState(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const handle = setTimeout(() => {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      getJSON(`/localities?${params.toString()}`)
        .then((body) => {
          setLocalities(body.localities);
          setNote(body.note);
          setError("");
        })
        .catch((exc) => setError(exc.message));
    }, 200);
    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    getJSON("/map")
      .then((body) => setPins(body.localities))
      .catch(() => setPins([]));
  }, []);

  useEffect(() => {
    if (!bhk && !verdict && !maxLakh) {
      setListings(null);
      return undefined;
    }
    const params = new URLSearchParams();
    const exact = localities.find((item) => item.name.toLowerCase() === query.trim().toLowerCase());
    if (exact) params.set("locality", exact.name);
    if (bhk) params.set("bhk", bhk);
    if (verdict) params.set("verdict", verdict);
    if (maxLakh) params.set("max_price", String(Number(maxLakh) * 100000));
    params.set("sort", "gap");
    params.set("limit", "12");
    getJSON(`/listings?${params.toString()}`)
      .then((body) => setListings(body))
      .catch((exc) => setError(exc.message));
    return undefined;
  }, [query, bhk, verdict, maxLakh, localities]);

  const visiblePins = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return pins;
    return pins.filter((item) => item.name.toLowerCase().includes(needle));
  }, [pins, query]);

  return (
    <section>
      <div className="hero">
        <p className="eyebrow">Bengaluru asking prices</p>
        <h1>See whether the ask sits inside the range.</h1>
        <p className="lede">
          Search a neighbourhood, then open a past listing to see the model range, the full buyer cost, and the commute.
        </p>
      </div>
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <label className="grow">
          Locality
          <input
            value={query}
            placeholder="Whitefield, Indiranagar, JP Nagar"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <label>
          BHK
          <select value={bhk} onChange={(event) => setBhk(event.target.value)}>
            <option value="">Any</option>
            {[1, 2, 3, 4].map((value) => (
              <option key={value} value={value}>{value}</option>
            ))}
          </select>
        </label>
        <label>
          Verdict
          <select value={verdict} onChange={(event) => setVerdict(event.target.value)}>
            <option value="">Any</option>
            <option value="great_deal">Great deal</option>
            <option value="fair">Fair</option>
            <option value="overpriced">Overpriced</option>
          </select>
        </label>
        <label>
          Max ask (₹ lakh)
          <input
            type="number"
            min="1"
            value={maxLakh}
            placeholder="80"
            onChange={(event) => setMaxLakh(event.target.value)}
          />
        </label>
      </form>
      {error ? <p className="callout">{error}</p> : null}
      <div className="split">
        <MapView localities={visiblePins} onSelect={(item) => navigate(`/locality/${encodeURIComponent(item.name)}`)} />
        <div className="stack">
          <p className="muted">{note}</p>
          {localities.map((item) => (
            <button
              key={item.name}
              type="button"
              className="card"
              onClick={() => navigate(`/locality/${encodeURIComponent(item.name)}`)}
            >
              <strong>{item.name}</strong>
              <span>{item.count} historical asks</span>
              <span>Median ask {inr(item.median_asking_inr)}</span>
              <span>Median model {inr(item.median_model_inr)}</span>
              <span>{pct(item.share_overpriced)} overpriced</span>
            </button>
          ))}
        </div>
      </div>
      {listings ? (
        <div className="block">
          <h2>{listings.total} matching asks</h2>
          <ListingRows listings={listings.listings} />
        </div>
      ) : null}
    </section>
  );
}

export function ListingRows({ listings }) {
  const navigate = useNavigate();
  if (!listings.length) return <p>No listings match these filters.</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>Locality</th>
          <th>BHK</th>
          <th>Area</th>
          <th>Ask</th>
          <th>Mid estimate</th>
          <th>Verdict</th>
        </tr>
      </thead>
      <tbody>
        {listings.map((item) => (
          <tr key={item.id} onClick={() => navigate(`/listing/${item.id}`)}>
            <td>{item.locality}</td>
            <td>{item.bhk}</td>
            <td>{Math.round(item.total_sqft)} sqft</td>
            <td>{inr(item.asking_inr)}</td>
            <td>{inr(item.p50_inr)}</td>
            <td>{item.verdict.replace("_", " ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
