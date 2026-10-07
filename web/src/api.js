const TOKEN_KEY = "hometruth-token";

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || "";
  } catch {
    return "";
  }
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function read(response) {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = body.detail;
    if (Array.isArray(detail)) {
      throw new Error(detail.map((item) => item.msg || JSON.stringify(item)).join(" "));
    }
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return body;
}

export function getJSON(path) {
  return fetch(path, { headers: { ...authHeaders() } }).then(read);
}

export function postJSON(path, payload) {
  return fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  }).then(read);
}

export function putJSON(path, payload) {
  return fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(payload),
  }).then(read);
}

export function deleteJSON(path) {
  return fetch(path, {
    method: "DELETE",
    headers: { ...authHeaders() },
  }).then(read);
}

export function listingToRequest(listing, buyer) {
  return {
    listing: {
      locality: listing.locality,
      total_sqft: listing.total_sqft,
      bhk: listing.bhk,
      bath: listing.bath,
      area_type: listing.area_type,
      ready_to_move: listing.ready_to_move,
      first_sale: Boolean(listing.first_sale),
      asking_price_inr: listing.asking_inr ?? listing.asking_price_inr,
      carpet_sqft: listing.carpet_sqft ?? null,
    },
    buyer: {
      net_monthly_income_inr: Number(buyer.net_monthly_income_inr),
      existing_monthly_emi_inr: Number(buyer.existing_monthly_emi_inr),
      down_payment_fraction: Number(buyer.down_payment_fraction),
      annual_interest_rate: Number(buyer.annual_interest_rate),
      tenure_years: Number(buyer.tenure_years),
      emi_ratio_cap: Number(buyer.emi_ratio_cap),
    },
    office_address: buyer.office_address?.trim() || null,
    assumptions: {
      appreciation: 0.05,
      rent_growth: 0.05,
      investment_return: 0.07,
      maintenance_rate: 0.005,
      gross_yield: null,
    },
  };
}
