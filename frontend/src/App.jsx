import { useState } from "react";
import SignalsPanel from "./components/SignalsPanel";
import TasksPanel   from "./components/TasksPanel";
import RatingPanel  from "./components/RatingPanel";
import StatsPanel   from "./components/StatsPanel";

export default function App() {
  const [mainTab, setMainTab] = useState("calls");
  const today = new Date().toLocaleDateString("uz-UZ");

  return (
    <div className="min-h-screen" style={{ background: "#0F1117" }}>
      <header style={{ background: "#1A1D2E", borderBottom: "1px solid #2A2D3E" }}
              className="px-5 py-3 flex items-center justify-between">
        <h1 className="text-xl font-bold text-white">CRM Dashboard</h1>
        <span className="text-xs" style={{ color: "#8B8FA8" }}>{today}</span>
      </header>

      <div className="p-4 space-y-4 max-w-7xl mx-auto">
        <nav className="flex gap-2">
          {[
            { id: "calls",    label: "📞 Qoʼngʼiroqlar" },
            { id: "telegram", label: "💬 Telegram" },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setMainTab(t.id)}
              className="px-5 py-2 rounded-full text-sm font-semibold transition-all"
              style={mainTab === t.id
                ? { background: "#4B6EF5", color: "#FFFFFF" }
                : { background: "#1A1D2E", color: "#8B8FA8", border: "1px solid #2A2D3E" }
              }
            >
              {t.label}
            </button>
          ))}
        </nav>

        {mainTab === "calls" && (
          <>
            <SignalsPanel />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <TasksPanel />
              <RatingPanel />
            </div>
            <StatsPanel view="calls" />
          </>
        )}

        {mainTab === "telegram" && (
          <StatsPanel view="telegram" />
        )}
      </div>
    </div>
  );
}
