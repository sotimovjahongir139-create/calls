import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getCallStats, getTelegramStats } from "../utils/api";

const CARD  = { background: "#1A1D2E", border: "1px solid #2A2D3E", boxShadow: "0 4px 20px rgba(0,0,0,0.3)" };
const BOX   = { background: "rgba(42,45,62,0.6)", border: "1px solid #2A2D3E" };
const TRACK = "#2A2D3E";

// ── shared UI ─────────────────────────────────────────────────────────────────

function PeriodToggle({ period, onChange }) {
  return (
    <div className="flex rounded-full p-0.5 gap-0.5" style={{ background: "#2A2D3E" }}>
      {[["daily", "KUNLIK"], ["monthly", "OYLIK"]].map(([val, lbl]) => (
        <button
          key={val}
          onClick={() => onChange(val)}
          className="px-4 py-1.5 rounded-full text-xs font-bold transition-all"
          style={period === val
            ? { background: "#4B6EF5", color: "#FFFFFF" }
            : { background: "transparent", color: "#8B8FA8", border: "1px solid transparent" }
          }
        >
          {lbl}
        </button>
      ))}
    </div>
  );
}

function MetricCard({ label, value, color = "#FFFFFF", highlight, icon }) {
  return (
    <div className="rounded-xl p-3 text-center flex-1 min-w-[80px]"
         style={highlight
           ? { background: "rgba(255,71,87,0.12)", border: "1px solid rgba(255,71,87,0.35)" }
           : { background: "#1A1D2E", border: "1px solid #2A2D3E" }
         }>
      {icon && <div className="text-base leading-none mb-0.5">{icon}</div>}
      <div className="text-2xl font-extrabold leading-tight" style={{ color }}>{value ?? "—"}</div>
      <div className="text-[10px] mt-1 leading-tight" style={{ color: "#8B8FA8" }}>{label}</div>
    </div>
  );
}

function Bar({ value, max, color = "#4B6EF5", label, suffix = "" }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-36 truncate shrink-0" style={{ color: "#8B8FA8" }}>{label}</span>
      <div className="flex-1 rounded-full overflow-hidden" style={{ background: TRACK, height: "8px" }}>
        <div className="h-full rounded-full transition-all duration-500"
             style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="w-12 text-right shrink-0 font-semibold text-white">{value}{suffix}</span>
    </div>
  );
}

function ProgressPct({ label, value, color = "#4B6EF5" }) {
  const pct = Math.min(Math.max(Number(value) || 0, 0), 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: "#8B8FA8" }}>{label}</span>
        <span className="text-white font-bold">{pct.toFixed(1)}%</span>
      </div>
      <div className="rounded-full overflow-hidden" style={{ background: TRACK, height: "8px" }}>
        <div className="h-full rounded-full transition-all duration-500"
             style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function Box({ title, children }) {
  return (
    <div className="rounded-xl p-4 space-y-4" style={BOX}>
      <h3 className="text-xs font-bold uppercase tracking-widest" style={{ color: "#8B8FA8" }}>{title}</h3>
      {children}
    </div>
  );
}

function Loading() {
  return <div className="flex items-center justify-center h-40 text-sm" style={{ color: "#5A5D72" }}>Yuklanmoqda…</div>;
}
function NoData() {
  return <div className="flex items-center justify-center h-40 text-sm" style={{ color: "#5A5D72" }}>Ma&apos;lumot yo&apos;q</div>;
}

// ── CALLS view ─────────────────────────────────────────────────────────────────

const HOUR_SLOTS = [
  ["09:00–11:00", "h_09_11"],
  ["11:00–13:00", "h_11_13"],
  ["13:00–15:00", "h_13_15"],
  ["15:00–17:00", "h_15_17"],
  ["17:00–19:00", "h_17_19"],
  ["19:00–21:00", "h_19_21"],
  ["21:00–23:00", "h_21_23"],
];

function CallsView({ row, loading }) {
  if (loading) return <Loading />;
  if (!row)    return <NoData />;

  const missed_pct = row.total_calls > 0
    ? Math.round(row.missed_clients / row.total_calls * 100) : 0;
  const maxHour = Math.max(...HOUR_SLOTS.map(([, k]) => row[k] || 0), 1);

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        <MetricCard icon="📊" label="Jami"              value={row.total_calls}          />
        <MetricCard icon="📞" label="Kiruvchi"           value={row.incoming_answered}    />
        <MetricCard icon="📤" label="Chiquvchi"          value={row.outgoing_answered}    />
        <MetricCard icon="🔴" label="Propushenniy"       value={row.missed_clients}        color="#FF4757"  highlight />
        <MetricCard icon="✅" label="Qayta chiqilgan"    value={row.recalled_clients}      color="#00D4AA"  />
        <MetricCard icon="❌" label="Qayta chiqilmagan"  value={row.not_recalled_clients}  color="#FFA726"  />
        <MetricCard icon="📉" label="Propushenniy %"     value={`${missed_pct}%`}          color="#FF4757"  />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Box title="Propushenniy Natijasi">
          <div className="grid grid-cols-3 gap-3 text-center">
            {[
              { val: row.recalled_clients,     color: "#00D4AA", lbl: "✅ Qayta chiqilgan"   },
              { val: row.not_recalled_clients, color: "#FF4757", lbl: "❌ Qayta chiqilmagan" },
              { val: Number(row.avg_recall_minutes || 0).toFixed(1), color: "#4B6EF5", lbl: "⏱️ Aloqa (daq)" },
            ].map(({ val, color, lbl }) => (
              <div key={lbl} className="rounded-lg p-2" style={{ background: "#2A2D3E" }}>
                <div className="text-xl font-extrabold" style={{ color }}>{val}</div>
                <div className="text-[10px] mt-0.5" style={{ color: "#8B8FA8" }}>{lbl}</div>
              </div>
            ))}
          </div>
          <div className="space-y-3">
            <ProgressPct label="📞 Javob berish %"      value={row.answer_rate}   color="#4B6EF5" />
            <ProgressPct label="✅ Qayta chiqish %"     value={row.recall_rate}   color="#00D4AA" />
            <ProgressPct label="❌ Qayta chiqilmagan %" value={row.no_recall_pct} color="#FF4757" />
          </div>
        </Box>

        <Box title="Soat Bo'yicha">
          <div className="space-y-2">
            {HOUR_SLOTS.map(([label, key]) => (
              <Bar key={key} label={label} value={row[key] || 0} max={maxHour} color="#4B6EF5" />
            ))}
          </div>
        </Box>
      </div>
    </div>
  );
}

// ── TELEGRAM view ──────────────────────────────────────────────────────────────

function TelegramView({ row, loading }) {
  if (loading) return <Loading />;
  if (!row)    return <NoData />;

  const maxBar = Math.max(
    row.manager_messages || 0, row.client_messages  || 0,
    row.client_turns     || 0, row.answered_turns   || 0,
    row.waiting_turns    || 0, 1
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        <MetricCard label="Jami events"    value={row.total_events}                                        />
        <MetricCard label="Klient xabar"   value={row.client_messages}                                    />
        <MetricCard label="Manager xabar"  value={row.manager_messages}                                   />
        <MetricCard label="Javob darajasi" value={`${Number(row.response_rate || 0).toFixed(1)}%`}        color="#00D4AA" />
        <MetricCard label="Hal qilingan"   value={row.answered_turns}   color="#4B6EF5"                   />
        <MetricCard label="Kutilayotgan"   value={row.waiting_turns}    color="#FFA726"                   />
        <MetricCard label="O'rtacha (daq)" value={Number(row.avg_response_minutes || 0).toFixed(1)}       />
      </div>

      <Box title="Telegram Ko'rsatkichlari">
        <div className="space-y-3">
          <Bar label="Manager javoblari"    value={row.manager_messages || 0} max={maxBar} color="#4B6EF5" />
          <Bar label="Klient xabarlari"     value={row.client_messages  || 0} max={maxBar} color="#7C4DFF" />
          <Bar label="Klient murojaatlari"  value={row.client_turns     || 0} max={maxBar} color="#9C27B0" />
          <Bar label="Javob berilgan"       value={row.answered_turns   || 0} max={maxBar} color="#00D4AA" />
          <Bar label="Javob kutilayotgan"   value={row.waiting_turns    || 0} max={maxBar} color="#FFA726" />
        </div>
      </Box>

      <Box title="Javob Ko'rsatkichlari">
        <ProgressPct label="Javob berish darajasi" value={row.response_rate || 0} color="#00D4AA" />
        <div className="text-center rounded-lg p-3 mt-2" style={{ background: "#2A2D3E" }}>
          <div className="text-xl font-extrabold" style={{ color: "#4B6EF5" }}>
            {Number(row.avg_response_minutes || 0).toFixed(1)}
          </div>
          <div className="text-[10px] mt-0.5" style={{ color: "#8B8FA8" }}>⏱️ O&apos;rtacha javob (daq)</div>
        </div>
      </Box>
    </div>
  );
}

// ── main component ─────────────────────────────────────────────────────────────

export default function StatsPanel({ view = "calls" }) {
  const [period, setPeriod] = useState("daily");

  const fetchFn = useCallback(() => {
    if (view === "telegram") return getTelegramStats(period);
    return getCallStats(period);
  }, [view, period]);

  const { data, error, loading } = usePolling(fetchFn, 5 * 60_000, [view, period]);

  // calls returns {rows:[...]}, telegram returns flat dict
  const row = view === "calls"
    ? (data?.rows?.[0] ?? null)
    : (data && !data.error && data.total_events !== undefined ? data : null);

  const title = view === "telegram" ? "💬 Telegram Statistika" : "📞 Qoʼngʼiroqlar Statistika";

  return (
    <div className="rounded-xl p-4" style={CARD}>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <PeriodToggle period={period} onChange={setPeriod} />
      </div>

      {error && (
        <div className="text-xs mb-3 rounded-lg px-3 py-2"
             style={{ color: "#FF4757", background: "rgba(255,71,87,0.1)", border: "1px solid rgba(255,71,87,0.3)" }}>
          {error}
        </div>
      )}

      {view === "calls"
        ? <CallsView row={row} loading={loading} />
        : <TelegramView row={row} loading={loading} />
      }
    </div>
  );
}
