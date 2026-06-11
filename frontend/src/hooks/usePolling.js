import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Polls fetchFn every intervalMs.
 * @param {() => Promise<any>} fetchFn
 * @param {number} intervalMs
 * @param {any[]} deps - re-subscribe when these change
 */
export function usePolling(fetchFn, intervalMs, deps = []) {
  const [data,    setData]    = useState(null);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(true);
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;

  const load = useCallback(async () => {
    try {
      const result = await fetchRef.current();
      setData(result);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    setData(null);
    setLoading(true);
    setError(null);
    load();
    const id = setInterval(load, intervalMs);
    return () => clearInterval(id);
  }, [load, intervalMs]);

  return { data, error, loading, refresh: load };
}
