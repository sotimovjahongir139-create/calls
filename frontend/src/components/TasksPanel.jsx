import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getTasks, completeTask } from "../utils/api";

const SLA = {
  ok:      { card: "border-green-700  bg-green-900/10",  dot: "🟢", time: "text-green-300"  },
  warning: { card: "border-yellow-600 bg-yellow-900/10", dot: "🟡", time: "text-yellow-300" },
  breach:  { card: "border-red-600    bg-red-900/15",    dot: "🔴", time: "text-red-300"    },
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

  const tasks = (data?.tasks ?? []).filter(t => !optimistic.has(t.contact_id));
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
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-lg font-semibold text-white">Vazifalar</h2>
        <div className="text-right">
          <div className="text-xs text-slate-400">Umumiy deadline</div>
          <div className="text-sm font-semibold text-orange-300">{fmtMin(deadline)}</div>
        </div>
      </div>

      {error && <div className="text-red-400 text-xs mb-2">{error}</div>}
      {loading && <div className="bg-slate-700 rounded-xl animate-pulse h-24 mb-2" />}

      {!loading && tasks.length === 0 && !error && (
        <div className="flex-1 flex items-center justify-center text-slate-500 text-sm">
          Propushenniy yo'q
        </div>
      )}

      <div className="space-y-2 overflow-y-auto flex-1 pr-1">
        {tasks.map(task => {
          const s = SLA[task.sla_status] ?? SLA.ok;
          const busy = completing.has(task.contact_id);
          return (
            <div key={task.contact_id}
              className={`rounded-lg border p-3 flex items-center gap-3 transition-opacity ${s.card} ${busy ? "opacity-50" : ""}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span>{s.dot}</span>
                  <span className="font-mono text-sm text-white truncate">
                    {task.phone || `#${task.contact_id}`}
                  </span>
                </div>
                <div className="flex gap-3 text-xs text-slate-400">
                  <span>Kutgan: <strong className={s.time}>{task.waiting_minutes} daq</strong></span>
                  <span>Deadline: <strong className="text-orange-300">{fmtMin(task.deadline_minutes)}</strong></span>
                </div>
              </div>
              <button
                onClick={() => handleComplete(task.contact_id)}
                disabled={busy}
                className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-700 hover:bg-green-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {busy ? "…" : "Bajarildi"}
              </button>
            </div>
          );
        })}
      </div>

      <div className="mt-2 text-xs text-slate-500 text-right">
        {tasks.length} ta · har 1 daqiqada yangilanadi
      </div>
    </div>
  );
}
