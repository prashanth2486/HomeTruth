import { Link, Navigate } from "react-router-dom";

import { useAuth } from "../auth";
import { loadShortlist } from "../storage";

export default function Account() {
  const { user, ready, signedIn, logout } = useAuth();
  const saved = loadShortlist().length;

  if (ready && !signedIn) return <Navigate to="/login" replace />;
  if (!user) return <p>Loading account…</p>;

  return (
    <section className="auth-shell">
      <p className="eyebrow">Signed in</p>
      <h1>{user.name}</h1>
      <p className="muted">{user.email}</p>
      <div className="stat-grid">
        <div className="stat">
          <span>Shortlist on this account</span>
          <strong>{saved}</strong>
        </div>
        <div className="stat">
          <span>Synced loan numbers</span>
          <strong>{user.buyer_prefs ? "Yes" : "Not yet"}</strong>
        </div>
      </div>
      <p className="lede">
        Browse without signing in. When you are signed in, shortlist changes and “Your numbers” sync to this account.
        The prediction log still never stores income.
      </p>
      <div className="actions">
        <Link className="primary linkish" to="/shortlist">Open shortlist</Link>
        <button type="button" className="ghost" onClick={logout}>Sign out</button>
      </div>
    </section>
  );
}
