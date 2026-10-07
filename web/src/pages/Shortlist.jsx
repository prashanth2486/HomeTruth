import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getJSON } from "../api";
import { useAuth } from "../auth";
import { inr, verdictLabel } from "../format";
import { loadShortlist, saveShortlist } from "../storage";

export default function Shortlist() {
  const { signedIn } = useAuth();
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    function load() {
      const ids = loadShortlist();
      if (!ids.length) {
        setItems([]);
        return;
      }
      Promise.all(ids.map((id) => getJSON(`/listings/${id}`)))
        .then((rows) => setItems(rows.map((row) => row.listing)))
        .catch((exc) => setError(exc.message));
    }
    load();
    window.addEventListener("hometruth-shortlist", load);
    window.addEventListener("hometruth-auth", load);
    return () => {
      window.removeEventListener("hometruth-shortlist", load);
      window.removeEventListener("hometruth-auth", load);
    };
  }, []);

  function remove(id) {
    const next = loadShortlist().filter((item) => item !== id);
    saveShortlist(next);
    setItems((current) => current.filter((item) => item.id !== id));
  }

  return (
    <section>
      <p className="eyebrow">{signedIn ? "Synced to your account" : "On this browser"}</p>
      <h1>Shortlist</h1>
      <p className="muted">
        {signedIn ? (
          "Up to three homes. Changes save to your account."
        ) : (
          <>
            Up to three homes on this device. <Link to="/login">Sign in</Link> to keep them across visits.
          </>
        )}
      </p>
      {error ? <p className="callout">{error}</p> : null}
      {!items.length ? <p>Add a listing from its page. Compare needs two or three.</p> : null}
      <div className="card-row">
        {items.map((item) => (
          <article key={item.id} className="card static">
            <strong>{item.locality}</strong>
            <span>{item.bhk} BHK · {Math.round(item.total_sqft)} sqft</span>
            <span>Ask {inr(item.asking_inr)}</span>
            <span>{verdictLabel(item.verdict)}</span>
            <Link to={`/listing/${item.id}`}>Open</Link>
            <button type="button" className="text-button" onClick={() => remove(item.id)}>Remove</button>
          </article>
        ))}
      </div>
      {items.length >= 2 ? <Link className="primary linkish" to="/compare">Compare these</Link> : null}
    </section>
  );
}
