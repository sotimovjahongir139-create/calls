import { usePolling } from "../hooks/usePolling";
import { getSignals } from "../utils/api";

const SLA_TEXT  = { ok: "YASHIL", warning: "SARIQ", breach: "QIZIL" };
const SLA_COLOR = { ok: "text-green-600", warning: "text-yellow-600", breach: "text-red-600" };

export default function SignalsPanel() {
  const { data, error, loading } = usePolling(getSignals, 30_000);

  if (loading) return <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 animate-pulse h-40" />;
  if (error)   return <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-red-600 text-sm">{error}</div>;

  const { sla_breach = [], rating_warning = {}, info = {} } = data;
  const hasBreaches = sla_breach.length > 0;
  const ratingBad   = (rating_warning.completed_pct ?? 100) < 60;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-gray-900">⚡ Signallar</h2>
        <span className="text-xs text-gray-400">har 30 sek</span>
      </div>

      {/* SLA */}
      <div className={`rounded-lg border p-3 ${hasBreaches ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
        <div className="text-sm font-semibold mb-2 flex items-center gap-2">
          <span>{hasBreaches ? "🔴" : "🟢"}</span>
          <span className={hasBreaches ? "text-red-700" : "text-green-700"}>
            SLA buzilish{hasBreaches ? ` (${sla_breach.length})` : " yo'q"}
          </span>
        </div>
        {hasBreaches && (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-gray-400 text-left">
                <th className="pb-1 font-medium">Telefon</th>
                <th className="pb-1 font-medium text-right">Kutgan (daq)</th>
                <th className="pb-1 font-medium text-right">Holat</th>
              </tr>
            </thead>
            <tbody>
              {sla_breach.map((r, i) => (
                <tr key={i} className="border-t border-red-100">
                  <td className="py-1 font-mono text-gray-800">{r.phone || "—"}</td>
                  <td className={`py-1 text-right font-bold ${SLA_COLOR[r.sla_status]}`}>{r.waiting_minutes}</td>
                  <td className={`py-1 text-right ${SLA_COLOR[r.sla_status]}`}>{SLA_TEXT[r.sla_status]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Rating */}
      <div className={`rounded-lg border p-3 ${ratingBad ? "bg-yellow-50 border-yellow-200" : "bg-gray-50 border-gray-200"}`}>
        <div className="text-sm font-semibold mb-1 flex items-center gap-2">
          <span>{ratingBad ? "🟡" : "⭐"}</span>
          <span className={ratingBad ? "text-yellow-700" : "text-gray-700"}>Reyting</span>
        </div>
        <div className="flex gap-4 text-xs text-gray-500">
          <span>Bajarildi: <strong className="text-gray-900">{rating_warning.completed_pct ?? 0}%</strong></span>
          <span>Kechikkan: <strong className="text-yellow-600">{rating_warning.late_count ?? 0}</strong></span>
        </div>
      </div>

      {/* Info */}
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
        <div className="text-sm font-semibold mb-1 flex items-center gap-2">
          <span>🟢</span>
          <span className="text-gray-700">Axborot</span>
        </div>
        <div className="flex gap-4 text-xs text-gray-500 flex-wrap">
          <span>Yopilgan: <strong className="text-blue-600">{info.tasks_closed_today ?? 0}</strong></span>
          <span>Ochiq: <strong className="text-orange-600">{info.open_tasks ?? 0}</strong></span>
        </div>
      </div>
    </div>
  );
}
