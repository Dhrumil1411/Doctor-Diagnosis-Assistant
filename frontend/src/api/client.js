const BASE = "/api";
const TOKEN_KEY = "dda_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request(method, path, { body, isForm } = {}) {
  const headers = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body && !isForm) headers["Content-Type"] = "application/json";

  const resp = await fetch(BASE + path, {
    method,
    headers,
    ...(body
      ? { body: isForm ? new URLSearchParams(body) : JSON.stringify(body) }
      : {}),
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
  patch: (path, body) => request("PATCH", path, { body }),
  put: (path, body) => request("PUT", path, { body }),
};
