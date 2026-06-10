import { useState, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { getCallStats, getTelegramStats } from "../utils/api";

const TABS = [
  { id: "calls-daily",   label: "Qo'ng'iroqlar (kunlik)" },
  { id: "calls-monthly", label: "Qo'ng'iroqlar (oylik)"  },
  { id: "tg-daily",      label: "Telegram"               },
];

const COLS = {
  "calls-daily": [
    { key: "stat_date",           label: "Sana"                   },
    { key: "manager_name",        label: "Menejer"                },
    { key: "total_calls",         label: "Jami"                   },
    { key: "missed_clients",      label: "Propushenniy"           },
    { key: "recalled_clients",    label: "Qayta"                  },
    { key: "avg_recall_minutes",  label: "O'rtacha (daq)", fmt: f1 },
  ],
  "calls-monthly": [
    { key: "stat_month",       label: "Oy"           },
    { key: "manager_name",     label: "Menejer"      },
    { key: "total_calls",      label: "Jami"         },
    { key: "missed_clients",   label: "Propushenniy" },
    { key: "recalled_clients", label: "Qayta"        },
  ],
  "tg-daily": [
    { key: "report_date",          label: "Sana"              },
    { key: "report_name",          label: "Menejer"           },
    { key: "client_messages",      label: "Klient xabar"      },
    { key: "manager_messages",     label: "Manager xabar"     },
    { key: "answered_turns",       label: "Javob berildi"     },
    { key: "waiting_turns",        label: "Kutmoqda"          },
    { key: "response_rate",        label: "Javob %",  fmt: fpct },
    { key: "avg_response_minutes", label: "O'rtacha (daq)", fmt: f1 },
  ],
};

function f1(v)   { return v != null ? Number(v).toFixed(1) : "—"; }
function fpct(v) { return v != null ? `${Number(v).toFixed(1)}%` : "—"; }

export default function StatsPanel() {
  const [tab, setTab] = useState("calls-daily");

  const fetchFn = useCallback(() => {
    if (tab === "tg-daily")      return getTelegramStats();
    const type = tab === "calls-daily" ? "daily" : "monthly";
    return getCallStats(type);
  }, [tab]);

  const { data, error, loading } = usePolling(fetchFn, 5 * 60_000, [tab]);

  const cols = COLS[tab] || [];
  const rows = data?.rows ?? [];

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 className="text-lg font-semibold text-white">Statistika</h2>
        <div className="flex gap-1 flex-wrap">
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                tab === t.id
                  ? "bg-blue-600 text-white"
                  : "bg-slate-700 text-slate-300 hover:bg-slate-600"
              }`}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {error && <div className="text-red-400 text-xs mb-2">{error}</div>}

      <div className="overflow-x-auto rounded-lg">
        <table className="w-full text-xs text-slate-300">
          <thead>
            <tr className="bg-slate-700/50">
              {cols.map(c => (
                <th key={c.key} className="px-3 py-2 text-left text-slate-400 font-medium whitespace-nowrap">
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr><td colSpan={cols.length} className="px-3 py-4 text-center text-slate-500">Yuklanmoqda…</td></tr>
            )}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={cols.length} className="px-3 py-4 text-center text-slate-500">Ma'lumot yo'q</td></tr>
            )}
            {!loading && rows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "" : "bg-slate-700/20"}>
                {cols.map(c => (
                  <td key={c.key} className="px-3 py-2 whitespace-nowrap">
                    {c.fmt ? c.fmt(row[c.key]) : (row[c.key] ?? "—")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
