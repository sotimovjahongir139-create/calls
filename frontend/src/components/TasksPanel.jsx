import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getTasks, completeTask } from "../utils/api";

const CARD = { background: "#1A1D2E", border: "1px solid #2A2D3E", boxShadow: "0 4px 20px rgba(0,0,0,0.3)" };

const SLA = {
  ok:      { accent: "#00D4AA", dot: "🟢" },
  warning: { accent: "#FFA726", dot: "🟡" },
  breach:  { accent: "#FF4757", dot: "🔴" },
};

function fmtMin(m) {
  if (!m) return "0 daq";
  const h = Math.floor(m / 60), min = Math.round(m % 60);
  return h ? `${h}h ${min}daq` : `${min} daq`;
}

export default function TasksPanel() {
  const [optimistic, setOptimistic] = useState(new Set());
  const [completing, setCompleting] = useState(new Set());

  const fetchFn = useCallback(getTasks, []);
  const { data, error, loading, refresh } = usePolling(fetchFn, 60_000);

  const tasks    = (data?.tasks ?? []).filter(t => !optimistic.has(t.contact_id));
  const deadline = data?.total_deadline_minutes ?? 0;

  const handleComplete = async (id) => {
    setOptimistic(prev => new Set(prev).add(id));
    setCompleting(prev => new Set(prev).add(id));
    try {
      await completeTask(id);
    } catch {
      setOptimistic(prev => { const s = new Set(prev); s.delete(id); return s; });
      await refresh();
    } finally {
      setCompleting(prev => { const s = new Set(prev); s.delete(id); return s; });
    }
  };

  return (
    <div className="rounded-xl p-4 flex flex-col h-full" style={CARD}>
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-white">⏰ Vazifalar</h2>
        <div className="text-right">
          <div className="text-xs" style={{ color: "#8B8FA8" }}>Umumiy deadline</div>
          <div className="text-sm font-bold" style={{ color: "#FFA726" }}>{fmtMin(deadline)}</div>
        </div>
      </div>

      {error && (
        <div className="text-xs mb-2 rounded-lg px-3 py-2" style={{ color: "#FF4757", background: "rgba(255,71,87,0.1)" }}>
          {error}
        </div>
      )}
      {loading && <div className="rounded-xl animate-pulse h-24 mb-2" style={{ background: "#2A2D3E" }} />}

      {!loading && tasks.length === 0 && !error && (
        <div className="flex-1 flex items-center justify-center text-sm" style={{ color: "#5A5D72" }}>
          Propushenniy yo&apos;q
        </div>
      )}

      <div className="space-y-2 overflow-y-auto flex-1 pr-1">
        {tasks.map(task => {
          const s    = SLA[task.sla_status] ?? SLA.ok;
          const busy = completing.has(task.contact_id);
          return (
            <div key={task.contact_id}
                 className="rounded-lg p-3 flex items-center gap-3 transition-opacity"
                 style={{
                   background: "#1A1D2E",
                   border: "1px solid #2A2D3E",
                   borderLeft: `4px solid ${s.accent}`,
                   opacity: busy ? 0.5 : 1,
                 }}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span>{s.dot}</span>
                  <span className="font-mono text-sm font-bold text-white truncate">
                    {task.phone || `#${task.contact_id}`}
                  </span>
                </div>
                <div className="flex gap-3 text-xs" style={{ color: "#8B8FA8" }}>
                  <span>Kutgan: <strong style={{ color: s.accent }}>{task.waiting_minutes} daq</strong></span>
                  <span>Deadline: <strong style={{ color: "#FFA726" }}>{fmtMin(task.deadline_minutes)}</strong></span>
                </div>
              </div>
              <button
                onClick={() => handleComplete(task.contact_id)}
                disabled={busy}
                className="shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                style={{ background: "#00D4AA", color: "#0F1117" }}
              >
                {busy ? "…" : "✅ Bajarildi"}
              </button>
            </div>
          );
        })}
      </div>

      <div className="mt-2 text-xs text-right" style={{ color: "#5A5D72" }}>
        {tasks.length} ta · har 1 daqiqada yangilanadi
      </div>
    </div>
  );
}
