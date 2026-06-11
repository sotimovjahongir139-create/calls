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
export const getTelegramStats = (type="daily") => apiFetch(`/api/stats/telegram?type=${type}`);
export const clearTables      = ()             => apiFetch("/api/admin/clear-tables", { method: "POST" });
export const runEtl           = (script)       => apiFetch(`/api/admin/run-etl?script=${script}`, { method: "POST" });
