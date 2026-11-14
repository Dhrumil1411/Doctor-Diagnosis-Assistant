const rawApiUrl = (typeof import.meta !== "undefined" && import.meta.env) ? import.meta.env.VITE_API_URL : "";
const envUrl = rawApiUrl ? String(rawApiUrl).trim().replace(/\/+$/, "") : "";

// If VITE_API_URL is provided, normalize to ensure it points to the API root.
// If empty, defaults to same-origin "/api" (standard reverse proxy setup).
export const BASE = envUrl ? (envUrl.endsWith("/api") ? envUrl : `${envUrl}/api`) : "/api";
export const API_ORIGIN = envUrl ? envUrl.replace(/\/api$/, "") : "";

const TOKEN_KEY = "dda_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function formatErrorDetail(detail) {
  if (!detail) return "An unexpected error occurred.";
  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const formatted = detail.map((err) => {
      if (!err || typeof err !== "object") return String(err);
      const loc = Array.isArray(err.loc)
        ? err.loc.filter((p) => p !== "body" && p !== "__root__").join(" > ")
        : "";
      let msg = err.msg || "Invalid value";
      msg = msg.replace(/^Value error,\s*/i, "");
      return loc ? `${loc}: ${msg}` : msg;
    });
    return formatted.filter(Boolean).join("; ");
  }

  if (typeof detail === "object") {
    if (detail.msg) return String(detail.msg).replace(/^Value error,\s*/i, "");
    if (detail.message) return String(detail.message);
    return Object.entries(detail)
      .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
      .join("; ");
  }

  return String(detail);
}

export class ApiError extends Error {
  constructor(status, detail) {
    const readableMessage = formatErrorDetail(detail);
    super(readableMessage);
    this.status = status;
    this.detail = detail;
    this.readableMessage = readableMessage;
  }
}

async function request(method, path, { body, isForm, isMultipart } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body && !isForm && !isMultipart) headers["Content-Type"] = "application/json";

  let requestBody = undefined;
  if (body) {
    if (isMultipart) {
      requestBody = body; // Native FormData
    } else if (isForm) {
      requestBody = new URLSearchParams(body);
    } else {
      requestBody = JSON.stringify(body);
    }
  }

  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = path.startsWith("http://") || path.startsWith("https://")
    ? path
    : `${BASE}${normalizedPath}`;

  const resp = await fetch(url, {
    method,
    headers,
    ...(requestBody ? { body: requestBody } : {}),
  });

  if (resp.status === 401 && path !== "/auth/login") setToken(null);
  if (!resp.ok) throw new ApiError(resp.status, await errorDetail(resp));
  if (resp.status === 204) return null;
  return resp.json();
}

async function errorDetail(resp) {
  try {
    const data = await resp.json();
    return data.detail ?? data;
  } catch {
    return resp.statusText;
  }
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, { body }),
  postForm: (path, form) => request("POST", path, { body: form, isForm: true }),
  postMultipart: (path, formData) => request("POST", path, { body: formData, isMultipart: true }),
  patch: (path, body) => request("PATCH", path, { body }),
  put: (path, body) => request("PUT", path, { body }),
  delete: (path) => request("DELETE", path),
};
