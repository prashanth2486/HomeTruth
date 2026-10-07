import { getToken, putJSON } from "./api";

const BUYER_KEY = "hometruth-buyer";
const SHORTLIST_KEY = "hometruth-shortlist";

export const defaultBuyer = {
  net_monthly_income_inr: 150000,
  existing_monthly_emi_inr: 0,
  down_payment_fraction: 0.2,
  annual_interest_rate: 0.08,
  tenure_years: 20,
  emi_ratio_cap: 0.4,
  office_address: "Manyata Tech Park, Bengaluru",
};

export function loadBuyer() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(BUYER_KEY) || "null");
    return saved ? { ...defaultBuyer, ...saved } : { ...defaultBuyer };
  } catch {
    return { ...defaultBuyer };
  }
}

export function saveBuyer(buyer, { sync = true } = {}) {
  sessionStorage.setItem(BUYER_KEY, JSON.stringify(buyer));
  window.dispatchEvent(new Event("hometruth-buyer"));
  if (sync && getToken()) {
    putJSON("/auth/me/buyer", buyer).catch(() => {});
  }
}

export function loadShortlist() {
  try {
    const saved = JSON.parse(localStorage.getItem(SHORTLIST_KEY) || "[]");
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export function saveShortlist(ids, { sync = true } = {}) {
  const next = ids.slice(0, 3);
  localStorage.setItem(SHORTLIST_KEY, JSON.stringify(next));
  window.dispatchEvent(new Event("hometruth-shortlist"));
  if (sync && getToken()) {
    putJSON("/auth/me/shortlist", { listing_ids: next }).catch(() => {});
  }
}

export function toggleShortlist(id) {
  const current = loadShortlist();
  if (current.includes(id)) {
    saveShortlist(current.filter((item) => item !== id));
    return;
  }
  if (current.length >= 3) {
    throw new Error("Compare holds 3 listings. Remove one first.");
  }
  saveShortlist([...current, id]);
}

export function applyAccountState(user) {
  if (!user) return;
  if (Array.isArray(user.shortlist)) {
    saveShortlist(user.shortlist, { sync: false });
  }
  if (user.buyer_prefs) {
    saveBuyer({ ...defaultBuyer, ...user.buyer_prefs }, { sync: false });
  }
}

export function mergeShortlists(serverIds, localIds) {
  const merged = [];
  for (const id of [...(serverIds || []), ...(localIds || [])]) {
    if (id && !merged.includes(id)) merged.push(id);
    if (merged.length >= 3) break;
  }
  return merged;
}
