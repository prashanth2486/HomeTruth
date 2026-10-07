import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { useAuth } from "./auth";
import BuyerPanel from "./components/BuyerPanel";
import Account from "./pages/Account";
import Check from "./pages/Check";
import Compare from "./pages/Compare";
import Home from "./pages/Home";
import Listing from "./pages/Listing";
import Locality from "./pages/Locality";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Shortlist from "./pages/Shortlist";
import { loadShortlist } from "./storage";

const DISCLAIMER =
  "HomeTruth is an estimate only. It is not an official valuation, a loan offer, or legal advice. The catalog is historical asking prices, not homes for sale today. Rent, appreciation, and the locality score are indicative. Commute time ignores live traffic.";

export default function App() {
  const { user, signedIn, logout } = useAuth();
  const [buyerOpen, setBuyerOpen] = useState(false);
  const [saved, setSaved] = useState(loadShortlist().length);

  useEffect(() => {
    const refresh = () => setSaved(loadShortlist().length);
    window.addEventListener("hometruth-shortlist", refresh);
    window.addEventListener("hometruth-auth", refresh);
    return () => {
      window.removeEventListener("hometruth-shortlist", refresh);
      window.removeEventListener("hometruth-auth", refresh);
    };
  }, []);

  return (
    <div className="app">
      <header className="top">
        <NavLink className="mark" to="/">HomeTruth</NavLink>
        <nav>
          <NavLink to="/">Search</NavLink>
          <NavLink to="/check">Check a price</NavLink>
          <NavLink to="/compare">Compare</NavLink>
          <NavLink to="/shortlist">Shortlist{saved ? ` (${saved})` : ""}</NavLink>
        </nav>
        <div className="top-actions">
          <button type="button" className="ghost" onClick={() => setBuyerOpen(true)}>Your numbers</button>
          {signedIn ? (
            <>
              <NavLink className="ghost linkish" to="/account">{user?.name?.split(" ")[0] || "Account"}</NavLink>
              <button type="button" className="text-button" onClick={logout}>Sign out</button>
            </>
          ) : (
            <>
              <NavLink className="ghost linkish" to="/login">Sign in</NavLink>
              <NavLink className="primary linkish" to="/register">Create account</NavLink>
            </>
          )}
        </div>
      </header>
      <p className="disclaimer">{DISCLAIMER}</p>
      <main>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/locality/:name" element={<Locality />} />
          <Route path="/listing/:id" element={<Listing />} />
          <Route path="/check" element={<Check />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/shortlist" element={<Shortlist />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/account" element={<Account />} />
        </Routes>
      </main>
      <BuyerPanel open={buyerOpen} onClose={() => setBuyerOpen(false)} />
    </div>
  );
}
