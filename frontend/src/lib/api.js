import { useCallback, useMemo } from "react";
import { useAuth } from "@clerk/react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;
export const APP_TOKEN_KEY = "konnto_app_token";
export const PENDING_INVITE_KEY = "konnto_pending_invite";

export function getAppToken() {
  try {
    return localStorage.getItem(APP_TOKEN_KEY);
  } catch {
    return null;
  }
}

function errorMessage(json, status) {
  const d = json && json.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) return d.map((x) => x.msg || "Invalid value").join(", ");
  if (status === 401) return "Please sign in again.";
  if (status >= 500) return "Something went wrong. Please try again.";
  return "Something went wrong.";
}

export async function publicFetch(path, opts = {}) {
  const res = await fetch(`${API}${path}`, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(errorMessage(json, res.status));
    err.status = res.status;
    throw err;
  }
  return json;
}

export async function readSSE(res, onEvent) {
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      const line = chunk.split("\n").find((l) => l.startsWith("data: "));
      if (line) {
        try {
          onEvent(JSON.parse(line.slice(6)));
        } catch {
          /* ignore partial */
        }
      }
    }
  }
}

export function useApi() {
  const { getToken } = useAuth();

  const tokenFn = useCallback(async () => getAppToken() || (await getToken()), [getToken]);

  const request = useCallback(
    async (method, path, body, opts = {}) => {
      const token = await tokenFn();
      const headers = { Authorization: `Bearer ${token}` };
      let data;
      if (body instanceof FormData) data = body;
      else if (body !== undefined && method !== "GET") {
        headers["Content-Type"] = "application/json";
        data = JSON.stringify(body);
      }
      const res = await fetch(`${API}${path}`, { method, headers, body: data });
      if (opts.raw) return res;
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err = new Error(errorMessage(json, res.status));
        err.status = res.status;
        err.detail = json.detail;
        throw err;
      }
      return json;
    },
    [tokenFn]
  );

  const stream = useCallback(
    async (path, body, onEvent) => {
      const token = await tokenFn();
      const res = await fetch(`${API}${path}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        const err = new Error(errorMessage(json, res.status));
        err.status = res.status;
        throw err;
      }
      await readSSE(res, onEvent);
    },
    [tokenFn]
  );

  const blob = useCallback(
    async (path) => {
      const res = await request("GET", path, undefined, { raw: true });
      if (!res.ok) throw new Error("Couldn't load the file");
      return res.blob();
    },
    [request]
  );

  return useMemo(
    () => ({
      get: (p) => request("GET", p),
      post: (p, b) => request("POST", p, b === undefined ? {} : b),
      put: (p, b) => request("PUT", p, b),
      patch: (p, b) => request("PATCH", p, b),
      del: (p) => request("DELETE", p),
      upload: (p, formData) => request("POST", p, formData),
      stream,
      blob,
      tokenFn,
    }),
    [request, stream, blob, tokenFn]
  );
}
