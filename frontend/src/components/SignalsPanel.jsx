import { usePolling } from "../hooks/usePolling";
import { getSignals } from "../utils/api";

const SLA_TEXT  = { ok: "YASHIL", warning: "SARIQ", breach: "QIZIL" };
const SLA_COLOR = { ok: "text-green-400", warning: "text-yellow-400", breach: "text-red-400" };

export default function SignalsPanel() {
  const { data, error, loading } = usePolling(getSignals, 30_000);

  if (loading) return <Skeleton />;
  if (error)   return <ErrBox msg={error} />;

  const { sla_breach = [], rating_warning = {}, info = {} } = data;
  const hasBreaches = sla_breach.length > 0;
  const ratingBad   = (rating_warning.completed_pct ?? 100) < 60;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4 space-y-3">
      <Header title="Signallar" subtitle="har 30 sek" />

      {/* SLA */}
      <div className={`rounded-lg border p-3 ${hasBreaches
        ? "bg-red-900/20 border-red-700"
        : "bg-green-900/10 border-green-800"}`}>
        <div className="text-sm font-medium mb-2 flex items-center gap-2">
          <span>{hasBreaches ? "🔴" : "🟢"}</span>
          <span className={hasBreaches ? "text-red-300" : "text-green-300"}>
            SLA buzilish{hasBreaches ? ` (${sla_breach.length})` : " yo'q"}
          </span>
        </div>
        {hasBreaches && (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-slate-500 text-left">
                <th className="pb-1">Telefon</th>
                <th className="pb-1 text-right">Kutgan (daq)</th>
                <th className="pb-1 text-right">Holat</th>
              </tr>
            </thead>
            <tbody>
              {sla_breach.map((r, i) => (
                <tr key={i} className="border-t border-slate-700">
                  <td className="py-1 font-mono text-slate-200">{r.phone || "—"}</td>
                  <td className={`py-1 text-right font-semibold ${SLA_COLOR[r.sla_status]}`}>
                    {r.waiting_minutes}
                  </td>
                  <td className={`py-1 text-right text-xs ${SLA_COLOR[r.sla_status]}`}>
                    {SLA_TEXT[r.sla_status]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Rating */}
      <div className={`rounded-lg border p-3 ${ratingBad
        ? "bg-yellow-900/20 border-yellow-700"
        : "bg-slate-700/30 border-slate-600"}`}>
        <div className="text-sm font-medium mb-1 flex items-center gap-2">
          <span>{ratingBad ? "🟡" : "⭐"}</span>
          <span className={ratingBad ? "text-yellow-300" : "text-slate-300"}>Reyting</span>
        </div>
        <div className="flex gap-4 text-xs text-slate-400">
          <span>Bajarildi: <strong className="text-white">{rating_warning.completed_pct ?? 0}%</strong></span>
          <span>Kechikkan: <strong className="text-yellow-400">{rating_warning.late_count ?? 0}</strong></span>
        </div>
      </div>

      {/* Info */}
      <div className="bg-slate-700/20 border border-slate-600 rounded-lg p-3">
        <div className="text-sm font-medium mb-1 flex items-center gap-2">
          <span>🟢</span>
          <span className="text-slate-300">Axborot</span>
        </div>
        <div className="flex gap-4 text-xs text-slate-400 flex-wrap">
          <span>Yopilgan: <strong className="text-blue-400">{info.tasks_closed_today ?? 0}</strong></span>
          <span>Ochiq: <strong className="text-orange-400">{info.open_tasks ?? 0}</strong></span>
        </div>
      </div>
    </div>
  );
}

function Header({ title, subtitle }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-lg font-semibold text-white">{title}</h2>
      <span className="text-xs text-slate-400">{subtitle}</span>
    </div>
  );
}
function Skeleton() {
  return <div className="bg-slate-800 rounded-xl p-4 animate-pulse h-40" />;
}
function ErrBox({ msg }) {
  return (
    <div className="bg-red-900/20 border border-red-700 rounded-xl p-4 text-red-400 text-sm">
      {msg}
    </div>
  );
}
