const BASE = import.meta.env.VITE_API_URL ?? "";

async function apiFetch(path, options = {}) {
  const res = await fetch(BASE + path, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const getSignals      = ()           => apiFetch("/api/signals");
export const getTasks        = ()           => apiFetch("/api/tasks");
export const completeTask    = (id)         => apiFetch(`/api/tasks/${id}/complete`, { method: "POST" });
export const getRatings      = (d)          => apiFetch(`/api/ratings${d ? `?date=${d}` : ""}`);
export const getCallStats    = (type="daily") => apiFetch(`/api/stats/calls?type=${type}`);
export const getTelegramStats = ()          => apiFetch("/api/stats/telegram");
