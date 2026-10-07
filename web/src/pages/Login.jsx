import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function Login() {
  const { login, signedIn, ready } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const next = location.state?.from || "/shortlist";

  if (ready && signedIn) return <Navigate to={next} replace />;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login({ email, password });
      navigate(next, { replace: true });
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-shell">
      <p className="eyebrow">Your account</p>
      <h1>Sign in</h1>
      <p className="lede">
        Search without an account. Sign in to keep a shortlist and your loan numbers across visits on this device.
      </p>
      <form className="auth-form" onSubmit={submit}>
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error ? <p className="callout">{error}</p> : null}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted">
        New here? <Link to="/register">Create an account</Link>
      </p>
    </section>
  );
}
