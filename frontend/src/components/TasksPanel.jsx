import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getTasks, completeTask } from "../utils/api";

const SLA = {
  ok:      { card: "border-l-green-500",  dot: "🟢", time: "text-green-600"  },
  warning: { card: "border-l-yellow-500", dot: "🟡", time: "text-yellow-600" },
  breach:  { card: "border-l-red-500",    dot: "🔴", time: "text-red-600"    },
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
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-base font-semibold text-gray-900">⏰ Vazifalar</h2>
        <div className="text-right">
          <div className="text-xs text-gray-400">Umumiy deadline</div>
          <div className="text-sm font-bold text-orange-500">{fmtMin(deadline)}</div>
        </div>
      </div>

      {error && <div className="text-red-600 text-xs mb-2 bg-red-50 rounded-lg px-3 py-2">{error}</div>}
      {loading && <div className="bg-gray-100 rounded-xl animate-pulse h-24 mb-2" />}

      {!loading && tasks.length === 0 && !error && (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          Propushenniy yo&apos;q
        </div>
      )}

      <div className="space-y-2 overflow-y-auto flex-1 pr-1">
        {tasks.map(task => {
          const s    = SLA[task.sla_status] ?? SLA.ok;
          const busy = completing.has(task.contact_id);
          return (
            <div key={task.contact_id}
              className={`rounded-lg border border-gray-200 border-l-4 ${s.card} bg-white shadow-sm p-3 flex items-center gap-3 transition-opacity ${busy ? "opacity-50" : ""}`}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span>{s.dot}</span>
                  <span className="font-mono text-sm font-bold text-gray-900 truncate">
                    {task.phone || `#${task.contact_id}`}
                  </span>
                </div>
                <div className="flex gap-3 text-xs text-gray-500">
                  <span>Kutgan: <strong className={s.time}>{task.waiting_minutes} daq</strong></span>
                  <span>Deadline: <strong className="text-orange-500">{fmtMin(task.deadline_minutes)}</strong></span>
                </div>
              </div>
              <button
                onClick={() => handleComplete(task.contact_id)}
                disabled={busy}
                className="shrink-0 px-3 py-1.5 rounded-lg text-xs font-semibold bg-green-500 hover:bg-green-600 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
              >
                {busy ? "…" : "✅ Bajarildi"}
              </button>
            </div>
          );
        })}
      </div>

      <div className="mt-2 text-xs text-gray-400 text-right">
        {tasks.length} ta · har 1 daqiqada yangilanadi
      </div>
    </div>
  );
}
