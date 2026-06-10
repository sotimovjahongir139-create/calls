import { usePolling } from "../hooks/usePolling";
import { getRatings } from "../utils/api";

const GRADE = {
  A: { color: "text-green-400",  bg: "bg-green-900/30  border-green-600",  bar: "bg-green-500"  },
  B: { color: "text-blue-400",   bg: "bg-blue-900/30   border-blue-600",   bar: "bg-blue-500"   },
  C: { color: "text-yellow-400", bg: "bg-yellow-900/20 border-yellow-600", bar: "bg-yellow-500" },
  D: { color: "text-orange-400", bg: "bg-orange-900/20 border-orange-600", bar: "bg-orange-500" },
  E: { color: "text-red-400",    bg: "bg-red-900/20    border-red-600",    bar: "bg-red-500"    },
};

export default function RatingPanel() {
  const { data, error, loading } = usePolling(getRatings, 5 * 60_000);

  if (loading) return <div className="bg-slate-800 rounded-xl p-4 animate-pulse h-64" />;
  if (error)   return (
    <div className="bg-red-900/20 border border-red-700 rounded-xl p-4 text-red-400 text-sm">{error}</div>
  );

  const grade  = data?.grade ?? "E";
  const cfg    = GRADE[grade] ?? GRADE.E;
  const pct    = data?.pct ?? 0;
  const isFinal = new Date().getHours() >= 22;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">Reyting</h2>
        <span className="text-xs text-slate-400">har 5 daqiqada</span>
      </div>

      {/* Grade */}
      <div className={`rounded-xl border p-4 text-center mb-4 ${cfg.bg}`}>
        <div className="text-xs text-slate-400 mb-1">{isFinal ? "Yakuniy baho" : "Joriy baho"}</div>
        <div className={`text-7xl font-black leading-none ${cfg.color}`}>{grade}</div>
        <div className="text-sm text-slate-300 mt-1">{pct}%</div>
      </div>

      {/* Progress */}
      <div className="mb-4">
        <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${cfg.bar}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
        <div className="flex justify-between text-xs mt-1 text-slate-500">
          <span>A≥90 · B≥75 · C≥60 · D≥40</span>
          <span>{data?.total_score}/{data?.max_score} ball</span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-xs mt-auto">
        <Cell label="Jami"      value={data?.total_tasks}       color="text-white"        />
        <Cell label="Vaqtida"   value={data?.completed_on_time} color="text-green-400"    />
        <Cell label="Kechikkan" value={data?.completed_late}    color="text-yellow-400"   />
        <Cell label="Ochiq"     value={data?.open_tasks}        color="text-orange-400"   />
      </div>
    </div>
  );
}

function Cell({ label, value, color }) {
  return (
    <div className="bg-slate-700/40 rounded-lg p-2 text-center">
      <div className="text-slate-400">{label}</div>
      <div className={`font-bold text-lg ${color}`}>{value ?? 0}</div>
    </div>
  );
}
