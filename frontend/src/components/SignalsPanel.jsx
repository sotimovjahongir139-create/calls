import { usePolling } from "../hooks/usePolling";
import { getSignals } from "../utils/api";

const CARD  = { background: "#1A1D2E", border: "1px solid #2A2D3E", boxShadow: "0 4px 20px rgba(0,0,0,0.3)" };
const SLA_C = { ok: "#00D4AA", warning: "#FFA726", breach: "#FF4757" };
const SLA_T = { ok: "YASHIL",  warning: "SARIQ",   breach: "QIZIL"   };

export default function SignalsPanel() {
  const { data, error, loading } = usePolling(getSignals, 30_000);

  if (loading) return (
    <div className="rounded-xl p-4 animate-pulse h-40" style={CARD} />
  );
  if (error) return (
    <div className="rounded-xl p-4 text-sm" style={{ ...CARD, color: "#FF4757" }}>{error}</div>
  );

  const { sla_breach = [], rating_warning = {}, info = {} } = data;
  const hasBreaches = sla_breach.length > 0;
  const ratingBad   = (rating_warning.completed_pct ?? 100) < 60;

  return (
    <div className="rounded-xl p-4 space-y-3" style={CARD}>
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-white">⚡ Signallar</h2>
        <span className="text-xs" style={{ color: "#8B8FA8" }}>har 30 sek</span>
      </div>

      {/* SLA */}
      <Section accent="#FF4757" active={hasBreaches}>
        <div className="text-sm font-semibold mb-2 flex items-center gap-2">
          <span>{hasBreaches ? "🔴" : "🟢"}</span>
          <span style={{ color: hasBreaches ? "#FF4757" : "#00D4AA" }}>
            SLA buzilish{hasBreaches ? ` (${sla_breach.length})` : " yo'q"}
          </span>
        </div>
        {hasBreaches && (
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left" style={{ color: "#5A5D72" }}>
                <th className="pb-1 font-medium">Telefon</th>
                <th className="pb-1 font-medium text-right">Kutgan (daq)</th>
                <th className="pb-1 font-medium text-right">Holat</th>
              </tr>
            </thead>
            <tbody>
              {sla_breach.map((r, i) => (
                <tr key={i} style={{ borderTop: "1px solid #2A2D3E" }}>
                  <td className="py-1 font-mono text-white">{r.phone || "—"}</td>
                  <td className="py-1 text-right font-bold" style={{ color: SLA_C[r.sla_status] }}>
                    {r.waiting_minutes}
                  </td>
                  <td className="py-1 text-right" style={{ color: SLA_C[r.sla_status] }}>
                    {SLA_T[r.sla_status]}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      {/* Rating */}
      <Section accent="#FFA726" active={ratingBad}>
        <div className="text-sm font-semibold mb-1 flex items-center gap-2">
          <span>{ratingBad ? "🟡" : "⭐"}</span>
          <span style={{ color: ratingBad ? "#FFA726" : "#8B8FA8" }}>Reyting</span>
        </div>
        <div className="flex gap-4 text-xs" style={{ color: "#8B8FA8" }}>
          <span>Bajarildi: <strong className="text-white">{rating_warning.completed_pct ?? 0}%</strong></span>
          <span>Kechikkan: <strong style={{ color: "#FFA726" }}>{rating_warning.late_count ?? 0}</strong></span>
        </div>
      </Section>

      {/* Info */}
      <Section accent="#00D4AA" active={false}>
        <div className="text-sm font-semibold mb-1 flex items-center gap-2">
          <span>🟢</span>
          <span style={{ color: "#8B8FA8" }}>Axborot</span>
        </div>
        <div className="flex gap-4 text-xs flex-wrap" style={{ color: "#8B8FA8" }}>
          <span>Yopilgan: <strong style={{ color: "#4B6EF5" }}>{info.tasks_closed_today ?? 0}</strong></span>
          <span>Ochiq: <strong style={{ color: "#FFA726" }}>{info.open_tasks ?? 0}</strong></span>
        </div>
      </Section>
    </div>
  );
}

function Section({ accent, active, children }) {
  return (
    <div className="rounded-lg p-3"
         style={{
           borderLeft: `3px solid ${accent}`,
           border: `1px solid #2A2D3E`,
           borderLeftColor: accent,
           borderLeftWidth: "3px",
           background: active ? `${accent}10` : "rgba(42,45,62,0.4)",
         }}>
      {children}
    </div>
  );
}
