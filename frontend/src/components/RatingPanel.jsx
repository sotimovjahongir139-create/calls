import { usePolling } from "../hooks/usePolling";
import { getRatings } from "../utils/api";

const CARD = { background: "#1A1D2E", border: "1px solid #2A2D3E", boxShadow: "0 4px 20px rgba(0,0,0,0.3)" };

const GRADE = {
  A: { color: "#00D4AA", bg: "rgba(0,212,170,0.12)",  border: "rgba(0,212,170,0.3)",  bar: "#00D4AA" },
  B: { color: "#4B6EF5", bg: "rgba(75,110,245,0.12)", border: "rgba(75,110,245,0.3)", bar: "#4B6EF5" },
  C: { color: "#FFA726", bg: "rgba(255,167,38,0.12)", border: "rgba(255,167,38,0.3)", bar: "#FFA726" },
  D: { color: "#FFA726", bg: "rgba(255,167,38,0.12)", border: "rgba(255,167,38,0.3)", bar: "#FFA726" },
  E: { color: "#FF4757", bg: "rgba(255,71,87,0.12)",  border: "rgba(255,71,87,0.3)",  bar: "#FF4757" },
};

export default function RatingPanel() {
  const { data, error, loading } = usePolling(getRatings, 5 * 60_000);

  if (loading) return <div className="rounded-xl p-4 animate-pulse h-64" style={CARD} />;
  if (error)   return (
    <div className="rounded-xl p-4 text-sm" style={{ ...CARD, color: "#FF4757" }}>{error}</div>
  );

  const grade   = data?.grade ?? "E";
  const cfg     = GRADE[grade] ?? GRADE.E;
  const pct     = data?.pct ?? 0;
  const isFinal = new Date().getHours() >= 22;

  return (
    <div className="rounded-xl p-4 flex flex-col h-full" style={CARD}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-white">📊 Reyting</h2>
        <span className="text-xs" style={{ color: "#8B8FA8" }}>har 5 daqiqada</span>
      </div>

      {/* Grade box */}
      <div className="rounded-xl p-4 text-center mb-4"
           style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
        <div className="text-xs mb-1" style={{ color: "#8B8FA8" }}>
          {isFinal ? "Yakuniy baho" : "Joriy baho"}
        </div>
        <div className="text-7xl font-black leading-none" style={{ color: cfg.color }}>{grade}</div>
        <div className="text-sm font-semibold mt-1" style={{ color: cfg.color }}>{pct}%</div>
      </div>

      {/* Progress bar */}
      <div className="mb-4">
        <div className="rounded-full overflow-hidden" style={{ background: "#2A2D3E", height: "8px" }}>
          <div className="h-full rounded-full transition-all duration-500"
               style={{ width: `${Math.min(pct, 100)}%`, background: cfg.bar }} />
        </div>
        <div className="flex justify-between text-xs mt-1" style={{ color: "#5A5D72" }}>
          <span>A≥90 · B≥75 · C≥60 · D≥40</span>
          <span>{data?.total_score}/{data?.max_score} ball</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2 text-xs mt-auto">
        <Cell label="Jami"      value={data?.total_tasks}       color="#FFFFFF"   />
        <Cell label="Vaqtida"   value={data?.completed_on_time} color="#00D4AA"   />
        <Cell label="Kechikkan" value={data?.completed_late}    color="#FFA726"   />
        <Cell label="Ochiq"     value={data?.open_tasks}        color="#FFA726"   />
      </div>
    </div>
  );
}

function Cell({ label, value, color }) {
  return (
    <div className="rounded-lg p-2 text-center" style={{ background: "#2A2D3E" }}>
      <div className="text-xs" style={{ color: "#8B8FA8" }}>{label}</div>
      <div className="font-bold text-lg" style={{ color }}>{value ?? 0}</div>
    </div>
  );
}
