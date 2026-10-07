import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function Register() {
  const { register, signedIn, ready } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (ready && signedIn) return <Navigate to="/account" replace />;

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register({ name, email, password });
      navigate("/account", { replace: true });
    } catch (exc) {
      setError(exc.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-shell">
      <p className="eyebrow">Create account</p>
      <h1>Join HomeTruth</h1>
      <p className="lede">
        Free account. Passwords are hashed. Income is stored only if you choose to sync it from “Your numbers”.
      </p>
      <form className="auth-form" onSubmit={submit}>
        <label>
          Name
          <input
            autoComplete="name"
            required
            maxLength={120}
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
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
          Password (at least 8 characters)
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={72}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error ? <p className="callout">{error}</p> : null}
        <button className="primary" type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </section>
  );
}
