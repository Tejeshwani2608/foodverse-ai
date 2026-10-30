// Thin fetch wrapper for the FoodVerse FastAPI backend.
const BASE = import.meta.env.VITE_API_URL || "";

async function handle(res) {
  if (res.ok) return res.json();
  let detail = `Request failed (${res.status})`;
  try {
    const body = await res.json();
    detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    /* non-JSON error body */
  }
  throw new Error(detail);
}

export const getJSON = (path) => fetch(BASE + path).then(handle);

export const postJSON = (path, body) =>
  fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(handle);

export const postFile = (path, file) => {
  const fd = new FormData();
  fd.append("file", file);
  return fetch(BASE + path, { method: "POST", body: fd }).then(handle);
};

export const del = (path) => fetch(BASE + path, { method: "DELETE" }).then(handle);
