import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getCallStats, getTelegramStats } from "../utils/api";

// ── shared UI ────────────────────────────────────────────────────────────────

function PeriodToggle({ period, onChange }) {
  return (
    <div className="flex bg-slate-700 rounded-lg p-0.5 gap-0.5">
      {[["daily", "KUNLIK"], ["monthly", "OYLIK"]].map(([val, lbl]) => (
        <button
          key={val}
          onClick={() => onChange(val)}
          className={`px-4 py-1.5 rounded-md text-xs font-bold transition-colors ${
            period === val
              ? "bg-blue-600 text-white"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          {lbl}
        </button>
      ))}
    </div>
  );
}

function MetricCard({ label, value, color = "text-white", highlight }) {
  return (
    <div className={`rounded-xl p-3 text-center flex-1 min-w-[80px] ${highlight ? "bg-blue-900/40 border border-blue-700/40" : "bg-slate-700/50"}`}>
      <div className={`text-2xl font-extrabold leading-tight ${color}`}>
        {value ?? "—"}
      </div>
      <div className="text-[10px] text-slate-400 mt-1 leading-tight">{label}</div>
    </div>
  );
}

function Bar({ value, max, color = "bg-blue-500", label, suffix = "" }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-400 w-36 truncate shrink-0">{label}</span>
      <div className="flex-1 bg-slate-700 rounded-full h-3 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-slate-200 w-12 text-right shrink-0 font-medium">
        {value}{suffix}
      </span>
    </div>
  );
}

function ProgressPct({ label, value, color = "bg-blue-500" }) {
  const pct = Math.min(Math.max(Number(value) || 0, 0), 100);
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-400">{label}</span>
        <span className="text-slate-200 font-bold">{pct.toFixed(1)}%</span>
      </div>
      <div className="bg-slate-700 rounded-full h-3 overflow-hidden">
        <div
          className={`${color} h-full rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function LoadingOverlay({ cols }) {
  return (
    <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
      Yuklanmoqda…
    </div>
  );
}

function NoData() {
  return (
    <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
      Ma&apos;lumot yo&apos;q
    </div>
  );
}

// ── CALLS view ───────────────────────────────────────────────────────────────

const HOUR_SLOTS = [
  ["09:00–11:00", "h_09_11"],
  ["11:00–13:00", "h_11_13"],
  ["13:00–15:00", "h_13_15"],
  ["15:00–17:00", "h_15_17"],
  ["17:00–19:00", "h_17_19"],
  ["19:00–21:00", "h_19_21"],
  ["21:00–23:00", "h_21_23"],
];

function CallsView({ row, loading, period }) {
  if (loading) return <LoadingOverlay />;
  if (!row)    return <NoData />;

  const missed_pct = row.total_calls > 0
    ? Math.round(row.missed_clients / row.total_calls * 100)
    : 0;

  const maxHour = Math.max(...HOUR_SLOTS.map(([, k]) => row[k] || 0), 1);

  return (
    <div className="space-y-4">
      {/* Top metric cards */}
      <div className="flex gap-2 flex-wrap">
        <MetricCard label="Jami"              value={row.total_calls}          />
        <MetricCard label="Kiruvchi"           value={row.incoming_answered}    />
        <MetricCard label="Chiquvchi"          value={row.outgoing_answered}    />
        <MetricCard label="Propushenniy"       value={row.missed_clients}        color="text-red-400"   highlight />
        <MetricCard label="Qayta chiqilgan"    value={row.recalled_clients}      color="text-green-400" />
        <MetricCard label="Qayta chiqilmagan"  value={row.not_recalled_clients}  color="text-orange-400"/>
        <MetricCard label="Propushenniy %"     value={`${missed_pct}%`}          color="text-red-300"   />
      </div>

      {/* Bottom two boxes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left — PROPUSHENNIY NATIJASI */}
        <div className="bg-slate-700/30 border border-slate-600/40 rounded-xl p-4 space-y-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest">
            Propushenniy Natijasi
          </h3>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <div className="text-xl font-extrabold text-green-400">{row.recalled_clients}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">Qayta chiqilgan</div>
            </div>
            <div>
              <div className="text-xl font-extrabold text-red-400">{row.not_recalled_clients}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">Qayta chiqilmagan</div>
            </div>
            <div>
              <div className="text-xl font-extrabold text-blue-400">
                {Number(row.avg_recall_minutes || 0).toFixed(1)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Qayta aloqa (daq)</div>
            </div>
          </div>

          <div className="space-y-3 pt-1">
            <ProgressPct label="Javob berish %"      value={row.answer_rate}   color="bg-blue-500"   />
            <ProgressPct label="Qayta chiqish %"     value={row.recall_rate}   color="bg-green-500"  />
            <ProgressPct label="Qayta chiqilmagan %" value={row.no_recall_pct} color="bg-red-500"    />
          </div>
        </div>

        {/* Right — SOAT BO'YICHA */}
        <div className="bg-slate-700/30 border border-slate-600/40 rounded-xl p-4 space-y-2">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">
            Soat Bo&apos;yicha
          </h3>
          {HOUR_SLOTS.map(([label, key]) => (
            <Bar
              key={key}
              label={label}
              value={row[key] || 0}
              max={maxHour}
              color="bg-blue-500"
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── TELEGRAM view ─────────────────────────────────────────────────────────────

function TelegramView({ row, loading, period }) {
  if (loading) return <LoadingOverlay />;
  if (!row)    return <NoData />;

  const maxBar = Math.max(
    row.manager_messages || 0,
    row.client_messages  || 0,
    row.client_turns     || 0,
    row.answered_turns   || 0,
    row.waiting_turns    || 0,
    1
  );

  return (
    <div className="space-y-4">
      {/* Top metric cards */}
      <div className="flex gap-2 flex-wrap">
        <MetricCard label="Jami events"      value={row.total_events}                                              />
        <MetricCard label="Klient xabar"     value={row.client_messages}                                          />
        <MetricCard label="Manager xabar"    value={row.manager_messages}                                         />
        <MetricCard label="Javob darajasi"   value={`${Number(row.response_rate || 0).toFixed(1)}%`} color="text-green-400" highlight />
        <MetricCard label="Hal qilingan"     value={row.answered_turns}  color="text-blue-400"                    />
        <MetricCard label="Kutilayotgan"     value={row.waiting_turns}   color="text-orange-400"                  />
        <MetricCard label="O'rtacha (daq)"   value={Number(row.avg_response_minutes || 0).toFixed(1)}             />
      </div>

      {/* Bar chart */}
      <div className="bg-slate-700/30 border border-slate-600/40 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">
          Telegram Ko&apos;rsatkichlari
        </h3>
        <Bar label="Manager javoblari"    value={row.manager_messages || 0} max={maxBar} color="bg-blue-500"    />
        <Bar label="Klient xabarlari"     value={row.client_messages  || 0} max={maxBar} color="bg-indigo-500"  />
        <Bar label="Klient murojaatlari"  value={row.client_turns     || 0} max={maxBar} color="bg-violet-500"  />
        <Bar label="Javob berilgan"       value={row.answered_turns   || 0} max={maxBar} color="bg-green-500"   />
        <Bar label="Javob kutilayotgan"   value={row.waiting_turns    || 0} max={maxBar} color="bg-orange-500"  />
      </div>

      {/* Response rate progress */}
      <div className="bg-slate-700/30 border border-slate-600/40 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-widest mb-3">
          Javob Ko&apos;rsatkichlari
        </h3>
        <ProgressPct
          label="Javob berish darajasi"
          value={row.response_rate || 0}
          color="bg-green-500"
        />
        <div className="pt-2">
          <div className="text-center bg-slate-700/50 rounded-lg p-3">
            <div className="text-xl font-extrabold text-blue-400">
              {Number(row.avg_response_minutes || 0).toFixed(1)}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">O&apos;rtacha javob (daq)</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── main component ────────────────────────────────────────────────────────────

export default function StatsPanel({ view = "calls" }) {
  const [period, setPeriod] = useState("daily");

  const fetchFn = useCallback(() => {
    if (view === "telegram") return getTelegramStats(period);
    return getCallStats(period);
  }, [view, period]);

  const { data, error, loading } = usePolling(fetchFn, 5 * 60_000, [view, period]);

  const rows = data?.rows ?? [];
  const row  = rows[0] ?? null;

  const title = view === "telegram" ? "Telegram Statistika" : "Qoʼngʼiroqlar Statistika";

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <PeriodToggle period={period} onChange={setPeriod} />
      </div>

      {error && (
        <div className="text-red-400 text-xs mb-3 bg-red-900/20 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      {view === "calls" ? (
        <CallsView row={row} loading={loading} period={period} />
      ) : (
        <TelegramView row={row} loading={loading} period={period} />
      )}
    </div>
  );
}
