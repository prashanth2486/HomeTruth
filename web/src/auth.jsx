import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { getJSON, getToken, postJSON, putJSON, setToken } from "./api";
import { applyAccountState, loadShortlist, mergeShortlists, saveShortlist } from "./storage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const acceptAuth = useCallback(async (payload) => {
    setToken(payload.access_token);
    const local = loadShortlist();
    const merged = mergeShortlists(payload.user.shortlist, local);
    applyAccountState({ ...payload.user, shortlist: merged });
    if (merged.join("|") !== (payload.user.shortlist || []).join("|")) {
      const updated = await putJSON("/auth/me/shortlist", { listing_ids: merged });
      setUser(updated);
      window.dispatchEvent(new Event("hometruth-auth"));
      return updated;
    }
    setUser({ ...payload.user, shortlist: merged });
    window.dispatchEvent(new Event("hometruth-auth"));
    return payload.user;
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function boot() {
      if (!getToken()) {
        if (!cancelled) setReady(true);
        return;
      }
      try {
        const me = await getJSON("/auth/me");
        if (cancelled) return;
        const merged = mergeShortlists(me.shortlist, loadShortlist());
        applyAccountState({ ...me, shortlist: merged });
        if (merged.join("|") !== (me.shortlist || []).join("|")) {
          const updated = await putJSON("/auth/me/shortlist", { listing_ids: merged });
          if (!cancelled) setUser(updated);
        } else if (!cancelled) {
          setUser(me);
        }
      } catch {
        setToken("");
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setReady(true);
      }
    }
    boot();
    return () => {
      cancelled = true;
    };
  }, []);

  const register = useCallback(
    async (form) => acceptAuth(await postJSON("/auth/register", form)),
    [acceptAuth],
  );

  const login = useCallback(
    async (form) => acceptAuth(await postJSON("/auth/login", form)),
    [acceptAuth],
  );

  const logout = useCallback(() => {
    setToken("");
    setUser(null);
    window.dispatchEvent(new Event("hometruth-auth"));
  }, []);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return null;
    }
    const me = await getJSON("/auth/me");
    applyAccountState(me);
    setUser(me);
    return me;
  }, []);

  const value = useMemo(
    () => ({ user, ready, register, login, logout, refresh, signedIn: Boolean(user) }),
    [user, ready, register, login, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth needs AuthProvider");
  return value;
}
